from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.memory import memory
from app.nodes import (
    rewrite_query_node,
    supervisor_node,
    knowledge_node,
    personal_node,
    output_guard_node,
    summarize_node,
    should_summarize,
)
from app.logging_config import logger


# ===== 路由函数 =====
def router(state: AgentState) -> str:
    return state.get("next_agent", "personal")


# ===== 建图 =====
builder = StateGraph(AgentState)
builder.add_node("rewrite_query", rewrite_query_node)  # 新入口
builder.add_node("supervisor", supervisor_node)
builder.add_node("knowledge_agent", knowledge_node)
builder.add_node("personal_agent", personal_node)
builder.add_node("output_guard", output_guard_node)
builder.add_node("summarize", summarize_node)

builder.set_entry_point("rewrite_query")  # 每次请求先扩写query
builder.add_edge("rewrite_query", "supervisor")  # 扩写完再路由
builder.add_conditional_edges("supervisor", router, {
    "knowledge": "knowledge_agent",
    "personal": "personal_agent",
})
# Agent 输出 → 审查节点
builder.add_edge("knowledge_agent", "output_guard")
builder.add_edge("personal_agent", "output_guard")
# 审查通过 → 摘要判断 → summarize/END
builder.add_conditional_edges("output_guard", should_summarize, {
    "summarize": "summarize",
    END: END,
})
builder.add_edge("summarize", END)

graph = builder.compile(checkpointer=memory)
logger.info("Agent 图编译完成")
