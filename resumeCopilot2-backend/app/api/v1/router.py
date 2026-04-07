"""
API v1 路由總管 — 把所有子路由集中在這裡註冊。

main.py 只需要 include 這一個 router 就好。
"""

from fastapi import APIRouter

from app.api.v1 import analysis, conversations, resumes

router = APIRouter(prefix="/api/v1")

router.include_router(resumes.router)
router.include_router(analysis.router)
router.include_router(conversations.router)
