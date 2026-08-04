from langgraph.graph import END
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage
from app.state import AgentState
from app.models.llm import llm
from app.config import MESSAGE_THRESHOLD, KEEP_RECENT
from app.logging_config import logger


def summarize_node(state: AgentState):
    """自动/手动摘要历史对话，防止上下文溢出"""
    messages = state["messages"]
    if len(messages) < MESSAGE_THRESHOLD:
        logger.debug("消息数 %d < 阈值 %d，跳过摘要", len(messages), MESSAGE_THRESHOLD)
        return {}

    existing_summary = state.get("summary", "")

    # 构建摘要提示
    conversation_text = ""
    for msg in messages:
        role = "用户" if isinstance(msg, HumanMessage) else "助手"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)[:300]
        conversation_text += f"{role}: {content}\n"

    summary_prompt = f"""请用简短中文总结以下对话，抓住关键信息（500字以内）：

【已有摘要】{existing_summary if existing_summary else "无"}

【对话记录】
{conversation_text}

请输出新的综合摘要，包含：
1. 用户问了什么核心问题
2. 用户透露了哪些个人信息（名字、喜好等）
3. 重要的上下文以备后续对话使用

摘要："""

    try:
        new_summary = llm.invoke([HumanMessage(content=summary_prompt)]).content
        new_summary = new_summary.strip()[:500]  # 限制摘要长度
    except Exception as e:
        logger.warning("摘要生成失败: %s", e)
        new_summary = existing_summary or "（摘要生成失败）"

    # 删除旧消息（保留最近 KEEP_RECENT 条）
    delete_msgs = [RemoveMessage(id=m.id) for m in messages[:-KEEP_RECENT] if hasattr(m, "id") and m.id]

    # 将摘要注入为新 SystemMessage
    summary_msg = SystemMessage(content=f"📝 [历史摘要]\n{new_summary}")

    logger.info("摘要完成: %d 条消息 → 保留 %d 条 + 摘要 (%d 字)",
                len(messages), KEEP_RECENT, len(new_summary))

    return {
        "summary": new_summary,
        "messages": delete_msgs + [summary_msg],
    }


def should_summarize(state: AgentState) -> str:
    """条件边：消息过多时走摘要节点"""
    if len(state["messages"]) >= MESSAGE_THRESHOLD:
        return "summarize"
    return END
