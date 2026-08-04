import uuid
from langchain_core.messages import SystemMessage
from app.state import AgentState
from app.agents.personal import personal_agent
from app.agents.prompts import FOCUS_INSTRUCTION
from app.logging_config import logger


def personal_node(state: AgentState):
    """个人助手干活"""
    msg_count = len(state.get("messages", []))
    logger.debug("personal 节点收到 %d 条历史消息", msg_count)
    agent_messages = [SystemMessage(content=FOCUS_INSTRUCTION)] + list(state["messages"])
    resp = personal_agent.invoke(
        {"messages": agent_messages},
        {"configurable": {"thread_id": f"sub-personal-{uuid.uuid4()}"}, "recursion_limit": 50}
    )
    return {"messages": [resp["messages"][-1]]}
