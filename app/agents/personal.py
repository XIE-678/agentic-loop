from langgraph.prebuilt import create_react_agent
from app.models.llm import llm
from app.agents.prompts import PERSONAL_PROMPT
from app.tools import caculate_number

# ===== Personal Agent =====
personal_agent = create_react_agent(
    model=llm,
    prompt=PERSONAL_PROMPT,
    tools=[caculate_number],
)
