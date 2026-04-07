"""
Redis 連線設定 — 用於對話上下文快取。

使用 redis.asyncio 提供非同步存取。
"""

from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

# 建立 Redis 非同步連線實例
redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,  # 自動把 bytes 解碼成 str
)


async def get_redis() -> Redis:
    """
    FastAPI Depends() 注入用。
    直接回傳共用的 redis_client 實例。
    """
    return redis_client
