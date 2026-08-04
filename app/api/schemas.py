from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(description="用户的问题")
    thread_id: str = Field(default="default-user", description="用户ID，用于区分不同用户")


class ChatResponse(BaseModel):
    answer: str = Field(description="Agent 的回答")
    thread_id: str = Field(description="用户ID")


class SummarizeRequest(BaseModel):
    thread_id: str = Field(default="default-user", description="要摘要的用户ID")
