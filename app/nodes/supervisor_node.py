import re
import uuid
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from app.state import AgentState
from app.agents.supervisor import supervisor_agent
from app.logging_config import logger


# ===== 路由决策 Pydantic 模型（强校验）=====
class RouterDecision(BaseModel):
    """主管路由决策，强制 LLM 输出合法路由目标"""
    agent: Literal["knowledge", "personal"] = Field(
        description="路由目标：knowledge（联网/知识库）或 personal（本地助手）"
    )


def _parse_routing_decision(text: str) -> str:
    """用 Pydantic 强校验解析路由决策，失败时回退正则 → 默认 personal"""
    # 1️⃣ 优先：Pydantic 严格校验 JSON
    try:
        decision = RouterDecision.model_validate_json(text)
        return decision.agent
    except ValidationError:
        pass

    # 2️⃣ 兜底：正则提取 + Pydantic 二次校验
    m = re.search(r'"agent":\s*"(\w+)"', text)
    if m:
        try:
            decision = RouterDecision(agent=m.group(1))
            return decision.agent
        except ValidationError:
            pass

    # 3️⃣ 纯文本兜底：LLM 直接输出 "knowledge" 或 "personal"
    text_stripped = text.strip().lower()
    if text_stripped in ("knowledge", "personal"):
        logger.info("纯文本路由: %s", text_stripped)
        return text_stripped

    # 4️⃣ 最终降级
    logger.warning("无法解析路由决策，降级到 personal。原始输出: %s", text[:200])
    return "personal"


def supervisor_node(state: AgentState):
    """主管：判断 → 写 next_agent"""
    resp = supervisor_agent.invoke(
        {"messages": state["messages"]},
        {"configurable": {"thread_id": f"sub-supervisor-{uuid.uuid4()}"}, "recursion_limit": 50}
    )
    text = resp["messages"][-1].content
    name = _parse_routing_decision(text)
    logger.info("路由 → %s", name)
    return {"next_agent": name}
