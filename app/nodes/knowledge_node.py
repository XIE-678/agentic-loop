import uuid
from langchain_core.messages import SystemMessage
from app.state import AgentState
from app.agents.knowledge import knowledge_agent
from app.agents.prompts import FOCUS_INSTRUCTION
from app.tools.search_limit import reset_search_count, SEARCH_LIMIT
from app.logging_config import logger


def knowledge_node(state: AgentState):
    """知识专家干活 —— 注入扩写query提升检索质量"""
    reset_search_count()  # 每轮对话重置搜索计数

    expanded = state.get("expanded_queries", [])
    agent_messages = [SystemMessage(content=FOCUS_INSTRUCTION)] + list(state["messages"])

    if expanded:
        # 把扩写query作为系统提示注入，引导 agent 用这些关键词搜索
        hint = (
            "🔍 系统已为你生成以下精准检索关键词（请用 search_knowledge_base 或 search_web 逐一搜索，"
            "但注意 search_web 最多调用 {} 次）：\n".format(SEARCH_LIMIT)
            + "\n".join(f"  · {q}" for q in expanded)
        )
        agent_messages.append(SystemMessage(content=hint))
        logger.info("注入扩写query: %s", expanded)

    resp = knowledge_agent.invoke(
        {"messages": agent_messages},
        {"configurable": {"thread_id": f"sub-knowledge-{uuid.uuid4()}"}, "recursion_limit": 10}
    )
    return {"messages": [resp["messages"][-1]]}
