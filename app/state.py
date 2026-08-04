from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


# ===== 定义共享状态 =====
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 消息历史（自动追加）
    next_agent: str       # 主管决定下一agent
    expanded_queries: list[str]  # query扩写后的检索词列表
    summary: str          # 对话历史摘要（自动/手动触发）
