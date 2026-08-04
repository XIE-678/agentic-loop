import json as _json
import time
import sqlite3
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from langchain_core.messages import HumanMessage

from app.graph import graph
from app.api.schemas import ChatRequest, ChatResponse, SummarizeRequest
from app.api.middleware import LogMiddleware
from app.nodes.summarize import summarize_node
from app.config import KEEP_RECENT
from app.logging_config import logger


# ===== 定义路由 =====
app = FastAPI(title="多Agent助手")
app.add_middleware(LogMiddleware)


def extract_answer(state):
    """从 state 里提取最后一条有效回复"""
    for msg in reversed(state.get("messages", [])):
        content = getattr(msg, "content", "")
        if content and not content.strip().startswith("{"):
            return content
    return "抱歉，没有生成回复。"


# ===== 加载 UI HTML =====
_UI_HTML = (Path(__file__).parent.parent / "ui" / "index.html").read_text(encoding="utf-8")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """接收用户问题，返回 Agent 回答"""
    logger.info("[%s] 收到: %s", req.thread_id, req.question[:60])
    t0 = time.time()
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        final_state = graph.invoke(
            {"messages": [HumanMessage(content=req.question)]},
            config=config,
        )
        answer = extract_answer(final_state)
        logger.info("[%s] 回复 %d 字 (%.2fs)", req.thread_id, len(answer), time.time() - t0)
        return ChatResponse(answer=answer, thread_id=req.thread_id)
    except Exception as e:
        logger.error("[%s] 异常: %s", req.thread_id, e, exc_info=True)
        raise


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式输出：一个字一个字推给前端"""
    logger.info("[%s] 收到(stream): %s", req.thread_id, req.question[:60])
    t0 = time.time()
    config = {"configurable": {"thread_id": req.thread_id}}

    async def generate():
        nonlocal t0
        skip_json = False
        json_buf = ""
        token_count = 0
        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=req.question)]},
                config=config,
                version="v2",
            ):
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if not content:
                        continue

                    if skip_json:
                        json_buf += content
                        if "}" in json_buf or "]" in json_buf:
                            after = json_buf[json_buf.rindex("}") + 1:] if "}" in json_buf else json_buf[json_buf.rindex("]") + 1:]
                            skip_json = False
                            json_buf = ""
                            if after:
                                token_count += len(after)
                                yield f"data: {_json.dumps({'token': after}, ensure_ascii=False)}\n\n"
                        continue

                    stripped = content.strip()
                    if stripped and stripped[0] in "{[":
                        skip_json = True
                        json_buf = content
                        # 可能单 chunk 就包含完整 JSON
                        closer = "}" if stripped[0] == "{" else "]"
                        if closer in json_buf:
                            idx = json_buf.rindex(closer)
                            after = json_buf[idx + 1:]
                            skip_json = False
                            json_buf = ""
                            if after:
                                token_count += len(after)
                                yield f"data: {_json.dumps({'token': after}, ensure_ascii=False)}\n\n"
                        continue

                    token_count += len(content)
                    yield f"data: {_json.dumps({'token': content}, ensure_ascii=False)}\n\n"
            yield f"data: {_json.dumps({'done': True})}\n\n"
            logger.info("[%s] 流式回复 %d tokens (%.2fs)", req.thread_id, token_count, time.time() - t0)
        except Exception as e:
            logger.error("[%s] 流式异常: %s", req.thread_id, e, exc_info=True)
            raise

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/history/{thread_id}")
def history(thread_id: str):
    """查看某线程保存了几条记录"""
    db = sqlite3.connect("./chat_history.db")
    rows = db.execute(
        "select checkpoint_id, parent_checkpoint_id from checkpoints where thread_id=? order by rowid",
        (thread_id,)
    ).fetchall()
    db.close()
    return {"thread_id": thread_id, "checkpoints": len(rows), "detail": rows}


@app.post("/chat/summarize")
def summarize(req: SummarizeRequest):
    """手动触发对话摘要：压缩历史消息，生成摘要注入上下文"""
    config = {"configurable": {"thread_id": req.thread_id}}
    # 获取当前状态
    current_state = graph.get_state(config)
    if current_state.values is None:
        return {"ok": False, "msg": f"用户 {req.thread_id} 没有对话历史"}

    messages = current_state.values.get("messages", [])
    old_summary = current_state.values.get("summary", "")

    # 强制执行一次摘要
    result = summarize_node({
        "messages": messages,
        "next_agent": "",
        "expanded_queries": [],
        "summary": old_summary,
    })

    if not result:
        return {"ok": True, "msg": f"消息数 {len(messages)} 较少，无需摘要", "message_count": len(messages)}

    # 更新 graph 状态
    graph.update_state(config, result)
    logger.info("[%s] 手动摘要完成: %d 条 → 保留 %d 条 + 摘要", req.thread_id, len(messages), KEEP_RECENT)

    return {
        "ok": True,
        "msg": "摘要完成",
        "old_message_count": len(messages),
        "kept_recent": KEEP_RECENT,
        "summary": result["summary"],
    }


@app.post("/chat/clear")
def clear(req: SummarizeRequest):
    """清空指定用户的全部对话历史"""
    db = sqlite3.connect("./chat_history.db")
    db.execute("DELETE FROM checkpoints WHERE thread_id=?", (req.thread_id,))
    db.execute("DELETE FROM writes WHERE thread_id=?", (req.thread_id,))
    db.commit()
    db.close()
    logger.info("[%s] 历史已清空", req.thread_id)
    return {"ok": True, "msg": f"用户 {req.thread_id} 的对话历史已清空"}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_UI_HTML)
