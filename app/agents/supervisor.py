from langgraph.prebuilt import create_react_agent
from app.models.llm import supervisor_llm
from app.agents.prompts import SUPERVISOR_PROMPT

# ===== 主管 Agent（不用工具，只判断路由）=====
supervisor_agent = create_react_agent(
    model=supervisor_llm,
    prompt=SUPERVISOR_PROMPT,
    tools=[],
)
