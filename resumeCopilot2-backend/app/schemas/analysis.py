"""
分析結果的 Pydantic Schema。
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


# --- 請求 ---

class AnalysisCreate(BaseModel):
    """觸發分析時的請求格式"""
    mode: str = "general"  # general / hr / technical


# --- 回應 ---

class AnalysisResponse(BaseModel):
    """回傳分析結果"""
    id: uuid.UUID
    resume_id: uuid.UUID
    mode: str
    summary: str
    education_background: dict
    recommended_roles: list
    suggestions: list
    token_usage: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
