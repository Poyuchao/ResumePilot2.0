"""
履歷相關 ORM Model。

Resume：履歷主表，存原始文字
ResumeChunk：RAG 用的切片，每個 chunk 屬於某個 section
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Resume(Base):
    """履歷主表"""

    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # PDF 上傳時記錄原始檔名
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 關聯
    chunks: Mapped[list["ResumeChunk"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


class ResumeChunk(Base):
    """RAG 切片 — 把履歷按 section 分段，存入向量資料庫前先存一份到 PG"""

    __tablename__ = "resume_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    section_name: Mapped[str] = mapped_column(
        String(50), nullable=False  # education / experience / project
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # 關聯
    resume: Mapped["Resume"] = relationship(back_populates="chunks")
