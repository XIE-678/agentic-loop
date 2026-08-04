import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件，已有环境变量不会被覆盖

# ===== HuggingFace 镜像 =====
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# ===== LangSmith 监控 =====
# 从 .env 读取，未配置则默认关闭
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
os.environ.setdefault("LANGSMITH_PROJECT", "agent01")
# LANGSMITH_API_KEY 由 .env 提供，不设默认值

# ===== 搜索次数限制 =====
SEARCH_LIMIT = 3  # 每轮对话最多搜索次数

# ===== 对话摘要阈值 =====
MESSAGE_THRESHOLD = 12  # 超过此数量自动触发摘要
KEEP_RECENT = 4          # 摘要后保留最近 N 条消息
