"""
Conversation Service — 對話系統的商業邏輯。

完整對話流程：
1. 使用者對某份履歷建立一個 conversation session
2. 使用者送出問題（message）
3. 系統從 Chroma 檢索相關 chunks（只搜該份履歷的）
4. 把 chunks + 最近對話歷史 組成 context
5. 送給 LLM 產生回答
6. 把 user message + assistant message 都存進 DB
7. 回傳 AI 回覆
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
from app.services.vectorstore_service import search_chunks_by_resume
from app.services.llm_service import get_llm
from app.services.rag_service import PROMPT_TEMPLATES

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser


# --- 對話 CRUD ---

async def create_conversation(db: AsyncSession, resume_id: uuid.UUID) -> Conversation:
    """建立新的對話 session"""
    conversation = Conversation(resume_id=resume_id)
    db.add(conversation)
    await db.commit()

    # 重新查詢並預載 messages（async 模式下不能 lazy load）
    return await get_conversation(db, conversation.id)


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID
) -> Conversation | None:
    """取得對話（含所有 messages）"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()


async def list_conversations(
    db: AsyncSession, resume_id: uuid.UUID
) -> list[Conversation]:
    """列出某份履歷的所有對話"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.resume_id == resume_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_messages(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Message]:
    """取得某個對話的所有訊息（按時間排序）"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


# --- 核心：送訊息 + RAG 回答 ---

async def send_message(
    db: AsyncSession,
    conversation: Conversation,
    resume_id: uuid.UUID,
    user_content: str,
    mode: str = "general",
) -> Message:
    """
    處理使用者的一則訊息，回傳 AI 的回覆。

    流程：
    1. 從 Chroma 檢索相關 chunks（只搜這份履歷的）
    2. 從 DB 撈最近 10 則對話歷史
    3. 組合 prompt → 送 LLM → 拿到回覆
    4. 存 user message + assistant message 到 DB
    """

    # --- 1. RAG 檢索：從 Chroma 找最相關的 3 個 chunks ---
    retrieved_docs = search_chunks_by_resume(
        resume_id=resume_id,
        query=user_content,
        k=3,
    )
    context = "\n\n---\n\n".join(doc.page_content for doc in retrieved_docs)

    # 提取 citations（記錄用了哪些 chunks，方便前端標示來源）
    citations = [
        {
            "section_name": doc.metadata.get("section_name"),
            "chunk_index": doc.metadata.get("chunk_index"),
            "content_preview": doc.page_content[:100],
        }
        for doc in retrieved_docs
    ]

    # --- 2. 撈最近的對話歷史（最多 10 則）---
    recent_messages = await get_messages(db, conversation.id)
    recent_messages = recent_messages[-10:]  # 只取最近 10 則，控制 token

    chat_history = []
    for msg in recent_messages:
        if msg.role == "user":
            chat_history.append(HumanMessage(content=msg.content))
        else:
            chat_history.append(AIMessage(content=msg.content))

    # --- 3. 組合 prompt + 呼叫 LLM ---
    system_message = PROMPT_TEMPLATES.get(mode, PROMPT_TEMPLATES["general"])

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message + "\n\n參考的履歷內容：\n{context}"),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{question}"),
    ])

    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    # 呼叫 LLM（這裡會等 AI 回覆）
    ai_response = await chain.ainvoke({
        "context": context,
        "chat_history": chat_history,
        "question": user_content,
    })

    # 簡易 token 估算（用字數粗估，精確版需要用 tiktoken）
    token_usage = {
        "estimated_prompt_tokens": len(context + user_content) // 4,
        "estimated_completion_tokens": len(ai_response) // 4,
    }

    # --- 4. 存 user message + assistant message ---
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=ai_response,
        citations=citations,
        token_usage=token_usage,
    )
    db.add(assistant_msg)

    await db.commit()
    await db.refresh(assistant_msg)

    return assistant_msg


# --- Streaming 版：逐 token 產出 AI 回覆 ---

import json
from collections.abc import AsyncGenerator


async def send_message_stream(
    db: AsyncSession,
    conversation: Conversation,
    resume_id: uuid.UUID,
    user_content: str,
    mode: str = "general",
) -> AsyncGenerator[str, None]:
    """
    Streaming 版本的 send_message。
    用 SSE 格式 yield 每個 token，最後 yield 完整的 metadata（citations + token_usage）。

    SSE 事件格式：
    - event: token   → data 是一個 text chunk
    - event: citations → data 是 JSON（citations 陣列）
    - event: done    → data 是 JSON（token_usage + message_id）
    """

    # --- 1. RAG 檢索 ---
    retrieved_docs = search_chunks_by_resume(
        resume_id=resume_id,
        query=user_content,
        k=3,
    )
    context = "\n\n---\n\n".join(doc.page_content for doc in retrieved_docs)

    citations = [
        {
            "section_name": doc.metadata.get("section_name"),
            "chunk_index": doc.metadata.get("chunk_index"),
            "content_preview": doc.page_content[:100],
        }
        for doc in retrieved_docs
    ]

    # --- 2. 對話歷史 ---
    recent_messages = await get_messages(db, conversation.id)
    recent_messages = recent_messages[-10:]

    chat_history = []
    for msg in recent_messages:
        if msg.role == "user":
            chat_history.append(HumanMessage(content=msg.content))
        else:
            chat_history.append(AIMessage(content=msg.content))

    # --- 3. 組合 prompt ---
    system_message = PROMPT_TEMPLATES.get(mode, PROMPT_TEMPLATES["general"])

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message + "\n\n參考的履歷內容：\n{context}"),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{question}"),
    ])

    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    # 先送 citations
    yield f"event: citations\ndata: {json.dumps(citations, ensure_ascii=False)}\n\n"

    # --- 4. Streaming：逐 token 產出 ---
    full_response = ""
    async for chunk in chain.astream({
        "context": context,
        "chat_history": chat_history,
        "question": user_content,
    }):
        full_response += chunk
        yield f"event: token\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    # --- 5. 存 DB ---
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=user_content,
    )
    db.add(user_msg)

    token_usage = {
        "estimated_prompt_tokens": len(context + user_content) // 4,
        "estimated_completion_tokens": len(full_response) // 4,
    }

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=full_response,
        citations=citations,
        token_usage=token_usage,
    )
    db.add(assistant_msg)

    await db.commit()
    await db.refresh(assistant_msg)

    # 送完成事件
    done_data = {
        "message_id": str(assistant_msg.id),
        "token_usage": token_usage,
    }
    yield f"event: done\ndata: {json.dumps(done_data)}\n\n"
