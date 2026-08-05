from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.state import AgentState
from app.models.llm import supervisor_llm  # 用小模型做审查，省成本
from app.agents.prompts import OUTPUT_GUARD_PROMPT
from app.logging_config import logger


def output_guard_node(state: AgentState):
    """后处理：审查最后一条 AI 消息 → 不合规则清洗 → 替换"""
    messages = state.get("messages", [])
    if not messages:
        return {}

    # 找到最后一条 AI 消息
    last_ai = None
    for m in reversed(messages):
        if isinstance(m, AIMessage) or (hasattr(m, "type") and m.type == "ai"):
            last_ai = m
            break

    if last_ai is None:
        return {}

    original = last_ai.content if isinstance(last_ai.content, str) else str(last_ai.content)
    if not original.strip():
        return {}

    # 快速预检：如果原文已经很干净（短且无违规符号），跳过 LLM 调用
    quick_pass = True
    for char in "*#`_~|>":
        if char in original:
            quick_pass = False
            break
    if len(original) > 500:
        quick_pass = False  # 太长也需要审查

    if quick_pass:
        logger.info("输出审查：预检通过，跳过 LLM")
        return {}

    # LLM 审查 + 清洗
    logger.info("输出审查：LLM 审查中... (原文 %d 字)", len(original))
    try:
        resp = supervisor_llm.invoke([
            SystemMessage(content=OUTPUT_GUARD_PROMPT),
            HumanMessage(content=f"审查以下回复：\n\n{original}"),
        ])
        cleaned = resp.content.strip()
    except Exception as e:
        logger.warning("输出审查失败: %s，保留原文", e)
        return {}

    if cleaned == original:
        logger.info("输出审查：原文合规，保持不变")
        return {}

    logger.info("输出审查：已清洗 (%d 字 → %d 字)", len(original), len(cleaned))

    # 替换最后一条 AI 消息
    if hasattr(last_ai, "id") and last_ai.id:
        from langchain_core.messages import RemoveMessage
        new_ai = AIMessage(content=cleaned)
        return {"messages": [RemoveMessage(id=last_ai.id), new_ai]}

    return {"messages": [AIMessage(content=cleaned)]}
