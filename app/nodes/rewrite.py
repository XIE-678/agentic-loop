import json as _json
from langchain_core.messages import SystemMessage, HumanMessage
from app.state import AgentState
from app.models.llm import llm
from app.agents.prompts import QUERY_REWRITE_PROMPT
from app.logging_config import logger


def rewrite_query_node(state: AgentState):
    """入口节点：LLM 扩写用户模糊问题 → 存入 expanded_queries"""
    messages = state["messages"]
    if not messages:
        return {"expanded_queries": []}

    user_msg = messages[-1].content
    if not isinstance(user_msg, str) or len(user_msg.strip()) < 2:
        return {"expanded_queries": []}

    logger.info("Query 扩写中... 原文: %s", user_msg[:60])

    try:
        resp = llm.invoke([
            SystemMessage(content=QUERY_REWRITE_PROMPT),
            HumanMessage(content=user_msg),
        ])
        raw = resp.content.strip()
        # 提取 JSON 数组
        queries = _json.loads(raw)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            logger.info("Query 扩写结果: %s", queries)
            return {"expanded_queries": queries}
        else:
            logger.warning("扩写格式异常: %s", raw[:100])
            return {"expanded_queries": []}
    except Exception as e:
        logger.warning("Query 扩写失败: %s", e)
        return {"expanded_queries": []}
