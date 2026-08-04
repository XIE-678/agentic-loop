from langgraph.prebuilt import create_react_agent
from app.models.llm import llm
from app.agents.prompts import PERSONAL_PROMPT
from app.tools import get_current_weather, caculate_number, get_my_birthday, get_history, get_current_time

# ===== Personal Agent =====
personal_agent = create_react_agent(
    model=llm,
    prompt=PERSONAL_PROMPT,
    tools=[get_current_weather, caculate_number, get_my_birthday, get_history, get_current_time],
)
