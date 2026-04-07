"""
應用程式設定 — 從環境變數讀取所有設定值。

使用 pydantic-settings 自動讀 .env 檔，
程式中透過 get_settings() 取得設定實例。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """所有環境變數集中在這裡管理"""

    # --- 資料庫 ---
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/resume_copilot"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Chroma ---
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # --- LLM ---
    llm_provider: str = "openai"          # "openai" 或 "claude"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # --- 應用程式 ---
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",       # 自動讀取 .env 檔
        env_file_encoding="utf-8",
        case_sensitive=False,  # 環境變數不分大小寫
    )


@lru_cache
def get_settings() -> Settings:
    """
    取得設定實例（有快取，整個 app 生命週期只建立一次）。
    在 FastAPI 中常搭配 Depends() 注入使用。
    """
    return Settings()
