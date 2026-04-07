"""
PostgreSQL 資料庫連線設定。

使用 SQLAlchemy 2.0 async 模式：
- async engine：非同步資料庫引擎
- async session：非同步資料庫 session（每個 request 一個）
- Base：所有 ORM model 的父類別
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# 建立非同步引擎 — echo=True 會印出 SQL 方便開發除錯
engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
)

# Session 工廠 — 每次呼叫 async_session() 會產生一個新的 session
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """所有 ORM model 都繼承這個 Base"""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI 的 Depends() 用這個函式取得 DB session。
    用完自動關閉，不需要手動 close。

    用法：
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        yield session
