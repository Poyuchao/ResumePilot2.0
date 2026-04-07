"""
履歷相關 API endpoints。

所有路由都掛在 /api/v1/resumes 底下。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.resume import ResumeCreate, ResumeResponse
from app.services import resume_service
from app.services.pdf_service import extract_text_from_pdf
from app.services.chunking_service import chunk_resume
from app.services.vectorstore_service import store_chunks_to_vectorstore

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/", response_model=ResumeResponse, status_code=201)
async def create_resume(body: ResumeCreate, db: AsyncSession = Depends(get_db)):
    """上傳一份新履歷（純文字）"""
    resume = await resume_service.create_resume(db, body.original_text)

    # 自動 chunking + 存入向量資料庫
    chunks = chunk_resume(body.original_text)
    await resume_service.save_chunks(db, resume.id, chunks)
    store_chunks_to_vectorstore(resume.id, chunks)

    return resume


@router.post("/upload-pdf", response_model=ResumeResponse, status_code=201)
async def upload_pdf(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """
    上傳 PDF 履歷。

    流程：接收 PDF → 提取文字 → 存進資料庫
    前端用 multipart/form-data 上傳，欄位名稱為 "file"。
    """
    # 檢查檔案類型
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="只接受 PDF 檔案")

    # 讀取檔案內容
    file_bytes = await file.read()

    # 檢查檔案大小（限制 10MB）
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=400, detail="檔案大小不能超過 10MB")

    # 解析 PDF 提取文字
    try:
        text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 存進資料庫
    resume = await resume_service.create_resume(db, text, file_name=file.filename)

    # 自動 chunking + 存入向量資料庫
    chunks = chunk_resume(text)
    await resume_service.save_chunks(db, resume.id, chunks)
    store_chunks_to_vectorstore(resume.id, chunks)

    return resume


@router.get("/", response_model=list[ResumeResponse])
async def list_resumes(db: AsyncSession = Depends(get_db)):
    """取得所有履歷"""
    return await resume_service.get_all_resumes(db)


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """取得單一履歷"""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """刪除一份履歷"""
    deleted = await resume_service.delete_resume(db, resume_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume not found")
