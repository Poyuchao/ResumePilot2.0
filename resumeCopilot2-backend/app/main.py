"""
FastAPI 應用程式入口。

啟動方式：
    uvicorn app.main:app --reload

開發時加 --reload 會自動偵測檔案變更並重啟。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.db.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理。
    startup：建立資料庫 table（開發用，正式環境用 Alembic migration）
    shutdown：關閉資料庫連線
    """
    # --- Startup ---
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # --- Shutdown ---
    await engine.dispose()


app = FastAPI(
    title="ResumePilot API",
    description="AI 履歷分析與互動式問答工具",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 設定 — 允許前端開發伺服器存取
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 預設 port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載 API 路由
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    """健康檢查 endpoint"""
    return {"status": "ok"}
