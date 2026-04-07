"""
LLM Service — 用 LangChain 建立 LLM 實例。

LangChain 的核心概念：
- ChatModel：對話型 LLM，輸入 messages → 輸出 AI 回覆
- 不同 provider（OpenAI、Claude）有各自的 ChatModel 類別
- 但它們都實作相同的介面，所以後續程式碼不需要區分 provider
"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from app.config import get_settings


@lru_cache
def get_llm() -> BaseChatModel:
    """
    根據設定檔建立對應的 LangChain ChatModel。

    回傳型別是 BaseChatModel（共同介面），
    所以不管底層是 OpenAI 還是 Claude，呼叫方式都一樣：
        llm.invoke([messages])
    """
    settings = get_settings()

    if settings.llm_provider == "claude":
        return ChatAnthropic(
            model=settings.claude_model,
            api_key=settings.anthropic_api_key,
        )

    # 預設使用 OpenAI
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
    )
