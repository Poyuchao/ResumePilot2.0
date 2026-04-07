"""
對話相關 API endpoints。

掛在 /api/v1/resumes/{resume_id}/conversations 底下。

對話流程：
1. POST /conversations/          → 建立新對話 session
2. POST /conversations/{id}/messages → 送出問題，拿到 AI 回覆
3. GET  /conversations/          → 列出所有對話
4. GET  /conversations/{id}/messages → 取得對話歷史
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.conversation import ConversationResponse, MessageCreate, MessageResponse
from app.services import resume_service, conversation_service

router = APIRouter(prefix="/resumes/{resume_id}/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """建立新的對話 session"""
    # 確認履歷存在
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    conversation = await conversation_service.create_conversation(db, resume_id)
    return conversation


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(resume_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """列出某份履歷的所有對話"""
    resume = await resume_service.get_resume(db, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    return await conversation_service.list_conversations(db, resume_id)


@router.post("/{conversation_id}/messages/stream", status_code=200)
async def send_message_stream(
    resume_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Streaming 版的送訊息 — 用 SSE 逐 token 回傳 AI 回覆。

    SSE 事件：
    - event: citations → 引用的履歷段落
    - event: token     → 每個 text chunk
    - event: done      → 完成（含 token_usage）
    """
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.resume_id != resume_id:
        raise HTTPException(status_code=400, detail="Conversation does not belong to this resume")

    return StreamingResponse(
        conversation_service.send_message_stream(
            db=db,
            conversation=conversation,
            resume_id=resume_id,
            user_content=body.content,
            mode=body.mode,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    resume_id: uuid.UUID,
    conversation_id: uuid.UUID,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    在對話中送出訊息，取得 AI 回覆（非 streaming 版，一次回傳完整結果）。
    """
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.resume_id != resume_id:
        raise HTTPException(status_code=400, detail="Conversation does not belong to this resume")

    assistant_msg = await conversation_service.send_message(
        db=db,
        conversation=conversation,
        resume_id=resume_id,
        user_content=body.content,
        mode=body.mode,
    )
    return assistant_msg


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    resume_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得某個對話的所有訊息"""
    conversation = await conversation_service.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.resume_id != resume_id:
        raise HTTPException(status_code=400, detail="Conversation does not belong to this resume")

    return await conversation_service.get_messages(db, conversation_id)
