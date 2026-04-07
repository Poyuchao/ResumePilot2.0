"""
履歷 Service — 處理履歷的 CRUD 商業邏輯。

Service 層的角色：
- Router 負責接收 HTTP 請求、回傳回應
- Service 負責實際的資料處理邏輯
- 這樣拆開讓程式更好測試、更好維護
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume, ResumeChunk


async def create_resume(
    db: AsyncSession, original_text: str, file_name: str | None = None
) -> Resume:
    """建立新履歷（純文字或 PDF 解析後的文字都走這裡）"""
    resume = Resume(original_text=original_text, file_name=file_name)
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


async def get_resume(db: AsyncSession, resume_id: uuid.UUID) -> Resume | None:
    """根據 ID 取得履歷"""
    return await db.get(Resume, resume_id)


async def get_all_resumes(db: AsyncSession) -> list[Resume]:
    """取得所有履歷"""
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    return list(result.scalars().all())


async def save_chunks(
    db: AsyncSession, resume_id: uuid.UUID, chunks: list[dict]
) -> list[ResumeChunk]:
    """
    把切好的 chunks 存進 resume_chunks table。

    Args:
        chunks: chunking_service.chunk_resume() 回傳的 list of dict
                每個 dict 有 section_name, content, chunk_index
    """
    db_chunks = []
    for chunk in chunks:
        db_chunk = ResumeChunk(
            resume_id=resume_id,
            section_name=chunk["section_name"],
            content=chunk["content"],
            chunk_index=chunk["chunk_index"],
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)

    await db.commit()

    # refresh 拿回 DB 自動生成的 id
    for c in db_chunks:
        await db.refresh(c)

    return db_chunks


async def delete_resume(db: AsyncSession, resume_id: uuid.UUID) -> bool:
    """刪除履歷（連帶刪除 chunks、analysis、conversations）"""
    resume = await db.get(Resume, resume_id)
    if not resume:
        return False
    await db.delete(resume)
    await db.commit()
    return True
