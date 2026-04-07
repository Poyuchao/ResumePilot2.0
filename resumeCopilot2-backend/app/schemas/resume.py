"""
履歷相關的 Pydantic Schema — 定義 API 請求/回應的資料格式。

跟 ORM Model 的差別：
- Model = 資料庫長什麼樣（對應 table）
- Schema = API 輸入輸出長什麼樣（對應 JSON）
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


# --- 請求 (Request) ---

class ResumeCreate(BaseModel):
    """上傳履歷時的請求格式"""
    original_text: str


# --- 回應 (Response) ---

class ResumeResponse(BaseModel):
    """回傳履歷資料"""
    id: uuid.UUID
    original_text: str
    file_name: str | None = None  # PDF 上傳才會有檔名，純文字上傳為 None
    created_at: datetime

    model_config = {"from_attributes": True}  # 允許從 ORM model 轉換


class ResumeChunkResponse(BaseModel):
    """回傳 RAG 切片資料"""
    id: uuid.UUID
    section_name: str
    content: str
    chunk_index: int

    model_config = {"from_attributes": True}
