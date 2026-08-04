import os
from langchain_openai import ChatOpenAI

# ===== 大模型 =====
llm = ChatOpenAI(
    model="deepseek-v4-pro",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    streaming=True,
)

# supervisor 只做路由分类，用小模型省钱加速
supervisor_llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    streaming=True,
)
