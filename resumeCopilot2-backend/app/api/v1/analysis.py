"""
分析相關 API endpoints。

掛在 /api/v1/resumes/{resume_id}/analysis 底下。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.analysis import AnalysisCreate, AnalysisResponse
from app.services import resume_service, analysis_service

router = APIRouter(prefix="/resumes/{resume_id}/analysis", tags=["analysis"])


@router.post("/", response_model=AnalysisResponse, status_code=201)
async def create_analysis(
    resume_id: uuid.UUID,
    body: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
):
    """觸發 AI 分析履歷（可選 mode：general / hr / technical）"""
    # 1. 確認履歷存在
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # 2. 檢查該 mode 是否已分析過
    existing = await analysis_service.get_analysis(db, resume_id, body.mode)
    if existing:
        raise HTTPException(status_code=409, detail=f"Analysis with mode '{body.mode}' already exists")

    # 3. 呼叫 LLM 進行分析
    analysis = await analysis_service.create_analysis(db, resume, body.mode)
    return analysis


@router.get("/", response_model=list[AnalysisResponse])
async def list_analyses(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """取得履歷的所有分析結果（所有 mode）"""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    from sqlalchemy import select
    from app.models.analysis import ResumeAnalysis
    result = await db.execute(
        select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)
    )
    return list(result.scalars().all())


@router.get("/{mode}", response_model=AnalysisResponse)
async def get_analysis(resume_id: uuid.UUID, mode: str, db: AsyncSession = Depends(get_db)):
    """取得特定模式的分析結果"""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    analysis = await analysis_service.get_analysis(db, resume_id, mode)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis with mode '{mode}' not found")
    return analysis
