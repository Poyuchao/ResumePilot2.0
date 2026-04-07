"""
Analysis Service — 呼叫 LLM 分析履歷，並將結果存入 DB。

流程：
1. 從 DB 取得履歷原文
2. 用 LangChain 的 analysis chain 送給 LLM（依 mode 切換角色）
3. 解析 LLM 回傳的 JSON
4. 存入 resume_analyses table（包含 token 用量）
"""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import ResumeAnalysis
from app.models.resume import Resume
from app.services.rag_service import build_analysis_chain
from app.services.llm_service import get_llm


async def create_analysis(db: AsyncSession, resume: Resume, mode: str = "general") -> ResumeAnalysis:
    """
    用 AI 分析一份履歷，把結果存進 DB。

    跟之前的差異：
    - 加了 mode 參數，會影響 AI 的角色（一般顧問 / HR / 技術面試官）
    - 改用 llm.ainvoke() 直接呼叫，這樣可以拿到 token_usage
      （之前用 chain.ainvoke() 經過 StrOutputParser 後 token 資訊就丟失了）
    """
    # 建立 chain 的 prompt 部分（不含 LLM 和 parser）
    chain = build_analysis_chain(mode)

    # 用 LLM 的 ainvoke 取得完整回應（包含 token 用量）
    # chain.ainvoke 回傳的是 str，但我們需要 AIMessage 物件來取 token_usage
    llm = get_llm()
    prompt = chain.first  # chain 的第一步是 prompt
    messages = await prompt.ainvoke({"resume_text": resume.original_text})
    ai_response = await llm.ainvoke(messages)

    # 取得 token 用量
    token_usage = None
    if ai_response.usage_metadata:
        token_usage = {
            "prompt_tokens": ai_response.usage_metadata.get("input_tokens", 0),
            "completion_tokens": ai_response.usage_metadata.get("output_tokens", 0),
            "total_tokens": ai_response.usage_metadata.get("total_tokens", 0),
        }

    # 解析 JSON
    parsed = _parse_json(ai_response.content)

    # 存入 DB
    analysis = ResumeAnalysis(
        resume_id=resume.id,
        mode=mode,
        summary=parsed.get("summary", ""),
        education_background=parsed.get("education_background", {}),
        recommended_roles=parsed.get("recommended_roles", []),
        suggestions=parsed.get("suggestions", []),
        token_usage=token_usage,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


async def get_analysis(db: AsyncSession, resume_id: uuid.UUID, mode: str = "general") -> ResumeAnalysis | None:
    """從 DB 查詢某份履歷某個模式的分析結果"""
    result = await db.execute(
        select(ResumeAnalysis).where(
            ResumeAnalysis.resume_id == resume_id,
            ResumeAnalysis.mode == mode,
        )
    )
    return result.scalar_one_or_none()


def _parse_json(text: str) -> dict:
    """
    解析 LLM 回傳的 JSON。
    有時 LLM 會用 ```json ... ``` 包住，這裡把它清掉。
    """
    cleaned = text.strip()

    # 移除 markdown code block 標記
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1])

    return json.loads(cleaned)
