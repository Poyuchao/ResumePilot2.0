"""
履歷分析結果 ORM Model。

每份履歷可做多次 AI 分析（不同 mode），產出摘要、學歷背景、推薦職位、建議。
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ResumeAnalysis(Base):
    """履歷分析結果 — 一份履歷 + 一個 mode 對應一筆分析"""

    __tablename__ = "resume_analyses"

    # 同一份履歷 + 同一個 mode 只能有一筆分析
    __table_args__ = (
        UniqueConstraint("resume_id", "mode", name="uq_resume_mode"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="general"  # general / hr / technical
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    education_background: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    recommended_roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    suggestions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 關聯
    resume: Mapped["Resume"] = relationship(back_populates="analyses")
