import sqlite3
import random
import threading
import os as _os
from typing import Any, Sequence, Iterator, AsyncIterator
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointTuple,
    CheckpointMetadata,
    ChannelVersions,
    get_checkpoint_id,
    get_checkpoint_metadata,
)
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langchain_core.runnables import RunnableConfig
from app.logging_config import logger


class SqliteSaver(BaseCheckpointSaver[str]):
    """把对话存到 SQLite 里，关掉程序也不丢"""

    def __init__(self, db_path="./chat_history.db"):
        super().__init__(serde=JsonPlusSerializer())
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()

        with self._lock:
            self.conn.execute("""
                create table if not exists checkpoints (
                    thread_id text not null,
                    checkpoint_ns text not null default '',
                    checkpoint_id text not null,
                    parent_checkpoint_id text,
                    type text not null default 'json',
                    checkpoint blob,
                    metadata_type text not null default 'json',
                    metadata blob,
                    primary key (thread_id, checkpoint_ns, checkpoint_id)
                )
            """)
            self.conn.execute("""
                create table if not exists writes (
                    thread_id text not null,
                    checkpoint_ns text not null default '',
                    checkpoint_id text not null,
                    task_id text not null,
                    idx integer not null,
                    channel text not null,
                    type text not null default 'json',
                    value blob,
                    task_path text not null default '',
                    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
                )
            """)
            self.conn.execute("""
                create table if not exists blobs (
                    thread_id text not null,
                    checkpoint_ns text not null default '',
                    channel text not null,
                    version text not null,
                    type text not null,
                    value blob,
                    primary key (thread_id, checkpoint_ns, channel, version)
                )
            """)
            self.conn.commit()

    # ═══ 存 checkpoint ═══
    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        c = checkpoint.copy()
        channel_values = c.pop("channel_values", {})

        cp_type, cp_blob = self.serde.dumps_typed(c)
        meta_type, meta_blob = self.serde.dumps_typed(
            get_checkpoint_metadata(config, metadata)
        )

        with self._lock:
            for ch, ver in new_versions.items():
                if ch in channel_values:
                    blob_type, blob_bytes = self.serde.dumps_typed(channel_values[ch])
                else:
                    blob_type, blob_bytes = "empty", b""
                self.conn.execute(
                    "insert or replace into blobs(thread_id, checkpoint_ns, channel, version, type, value) "
                    "values(?, ?, ?, ?, ?, ?)",
                    (thread_id, checkpoint_ns, ch, ver, blob_type, blob_bytes),
                )

            self.conn.execute(
                "insert or replace into checkpoints(thread_id, checkpoint_ns, checkpoint_id, "
                "parent_checkpoint_id, type, checkpoint, metadata_type, metadata) "
                "values(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    thread_id, checkpoint_ns, checkpoint_id,
                    parent_checkpoint_id,
                    cp_type, cp_blob,
                    meta_type, meta_blob,
                ),
            )
            self.conn.commit()

        print(f"[SqliteSaver] put({thread_id}): 保存 checkpoint={checkpoint_id[:8]}...")
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    # ═══ 存 writes ═══
    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        with self._lock:
            for idx, (channel, value) in enumerate(writes):
                w_type, w_blob = self.serde.dumps_typed(value)
                self.conn.execute(
                    "insert or replace into writes(thread_id, checkpoint_ns, checkpoint_id, "
                    "task_id, idx, channel, type, value, task_path) values(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (thread_id, checkpoint_ns, checkpoint_id, task_id, idx, channel,
                     w_type, w_blob, task_path),
                )
            self.conn.commit()

    # ═══ 取 ═══
    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = get_checkpoint_id(config)

        with self._lock:
            if checkpoint_id:
                row = self.conn.execute(
                    "select checkpoint_id, type, checkpoint, metadata_type, metadata, parent_checkpoint_id "
                    "from checkpoints where thread_id=? and checkpoint_ns=? and checkpoint_id=?",
                    (thread_id, checkpoint_ns, checkpoint_id),
                ).fetchone()
            else:
                row = self.conn.execute(
                    "select checkpoint_id, type, checkpoint, metadata_type, metadata, parent_checkpoint_id "
                    "from checkpoints where thread_id=? and checkpoint_ns=? "
                    "order by rowid desc limit 1",
                    (thread_id, checkpoint_ns),
                ).fetchone()

        if row is None:
            print(f"[SqliteSaver] get_tuple({thread_id}): 未找到历史")
            return None
        print(f"[SqliteSaver] get_tuple({thread_id}): 恢复 checkpoint={row[0][:8]}...")

        cp_id, cp_type, cp_blob, meta_type, meta_blob, parent_cp_id = row

        ckpt: Checkpoint = self.serde.loads_typed((cp_type, cp_blob))
        metadata = self.serde.loads_typed((meta_type, meta_blob))

        with self._lock:
            write_rows = self.conn.execute(
                "select task_id, channel, type, value from writes "
                "where thread_id=? and checkpoint_ns=? and checkpoint_id=? "
                "order by idx",
                (thread_id, checkpoint_ns, cp_id),
            ).fetchall()

        channel_values: dict[str, Any] = {}
        versions = ckpt.get("channel_versions", {})
        for ch, ver in versions.items():
            row = self.conn.execute(
                "select type, value from blobs "
                "where thread_id=? and checkpoint_ns=? and channel=? and version=?",
                (thread_id, checkpoint_ns, ch, ver),
            ).fetchone()
            if row and row[0] != "empty":
                channel_values[ch] = self.serde.loads_typed((row[0], row[1]))

        pending_writes = [
            (tid, ch, self.serde.loads_typed((w_type, v)))
            for tid, ch, w_type, v in write_rows
        ]

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": cp_id,
                }
            },
            checkpoint={**ckpt, "channel_values": channel_values},
            metadata=metadata,
            pending_writes=pending_writes,
            parent_config=(
                {"configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": parent_cp_id,
                }}
                if parent_cp_id else None
            ),
        )

    # ═══ 列出所有 checkpoint ═══
    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        thread_ids = (config["configurable"]["thread_id"],) if config else None
        sql = "select thread_id, checkpoint_ns, checkpoint_id, type, checkpoint, metadata_type, metadata, parent_checkpoint_id from checkpoints"
        conds = []
        params = []
        if thread_ids:
            conds.append(f"thread_id in ({','.join('?' * len(thread_ids))})")
            params.extend(thread_ids)
        if before:
            bc_id = get_checkpoint_id(before)
            if bc_id:
                conds.append("checkpoint_id < ?")
                params.append(bc_id)
        if conds:
            sql += " where " + " and ".join(conds)
        sql += " order by checkpoint_id desc"
        if limit is not None:
            sql += " limit ?"
            params.append(limit)

        with self._lock:
            for row in self.conn.execute(sql, params):
                tid, ns, cid, cp_type, cp_blob, mt_type, mt_blob, p_cp_id = row
                ckpt = self.serde.loads_typed((cp_type, cp_blob))
                metadata = self.serde.loads_typed((mt_type, mt_blob))
                yield CheckpointTuple(
                    config={"configurable": {"thread_id": tid, "checkpoint_ns": ns, "checkpoint_id": cid}},
                    checkpoint=ckpt,
                    metadata=metadata,
                    parent_config=(
                        {"configurable": {"thread_id": tid, "checkpoint_ns": ns, "checkpoint_id": p_cp_id}}
                        if p_cp_id else None
                    ),
                )

    # ═══ 删除线程 ═══
    def delete_thread(self, thread_id: str) -> None:
        with self._lock:
            for table in ("checkpoints", "writes", "blobs"):
                self.conn.execute(f"delete from {table} where thread_id=?", (thread_id,))
            self.conn.commit()

    # ═══ 版本号 ═══
    def get_next_version(self, current: str | None, channel: None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(current.split(".")[0])
        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"

    # ═══ 异步方法 ═══
    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    async def alist(self, config, *, filter=None, before=None, limit=None) -> AsyncIterator[CheckpointTuple]:
        for item in self.list(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(self, config, checkpoint, metadata, new_versions) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path="") -> None:
        return self.put_writes(config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        return self.delete_thread(thread_id)


# ===== 创建 Memory 实例 =====
_db_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "chat_history.db")
memory = SqliteSaver(_db_path)
logger.info("数据库: %s", _db_path)
