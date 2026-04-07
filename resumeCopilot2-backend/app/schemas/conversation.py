"""
對話相關的 Pydantic Schema。
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


# --- 請求 ---

class MessageCreate(BaseModel):
    """使用者送出訊息"""
    content: str
    mode: str = "general"  # general / hr / technical


# --- 回應 ---

class MessageResponse(BaseModel):
    """回傳單則訊息"""
    id: uuid.UUID
    role: str
    content: str
    citations: list | None = None
    token_usage: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """回傳對話 session"""
    id: uuid.UUID
    resume_id: uuid.UUID
    created_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}
