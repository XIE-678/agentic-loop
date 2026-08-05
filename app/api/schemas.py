import uuid
from pydantic import BaseModel, Field

# 每次服务启动生成新的默认 thread_id
_STARTUP_THREAD_ID = "web-" + uuid.uuid4().hex[:12]


class ChatRequest(BaseModel):
    question: str = Field(description="用户的问题")
    thread_id: str = Field(default=_STARTUP_THREAD_ID, description="用户ID，用于区分不同用户")


class ChatResponse(BaseModel):
    answer: str = Field(description="Agent 的回答")
    thread_id: str = Field(description="用户ID")


class SummarizeRequest(BaseModel):
    thread_id: str = Field(default=_STARTUP_THREAD_ID, description="要摘要的用户ID")
