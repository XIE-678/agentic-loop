from langgraph.prebuilt import create_react_agent
from app.models.llm import llm
from app.agents.prompts import KNOWLEDGE_PROMPT
from app.tools import search_knowledge_base, search_web

# ===== Knowledge Agent =====
knowledge_agent = create_react_agent(
    model=llm,
    prompt=KNOWLEDGE_PROMPT,
    tools=[search_knowledge_base, search_web],
)
