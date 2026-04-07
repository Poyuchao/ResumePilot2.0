@AGENTS.md

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResumePilot 2.0 — AI 履歷分析與互動式問答工具。使用者匯入履歷，系統自動結構化分析，並支援多輪對話協助優化履歷。

## Workspace Structure

- `resumeCopilot2-backend/` — FastAPI (Python) backend
- `resumeCopilot2-frontend/` — Next.js (React) frontend

## Architecture

```
Frontend (Next.js / React)
        ↓ REST API
Backend (FastAPI)
        ↓
┌────────────────────────────────┐
│ AI 應用層                       │
│ - Prompt Templates (多模式分析)  │
│ - LLM (OpenAI / Claude)        │
│ - RAG 檢索 (Chroma vector DB)  │
└────────────────────────────────┘
        ↓
┌────────────────────────────────┐
│ 資料層                          │
│ - PostgreSQL：履歷、分析結果、對話 │
│ - Redis：對話上下文快取          │
│ - Chroma：履歷 chunks 向量存儲   │
└────────────────────────────────┘
```

## Key Design Decisions

- **DB**：使用 PostgreSQL 作為主要資料庫
- **RAG 策略**：Section-based chunking (education/experience/project)，chunk 300-600 字，top-K=3，context = 摘要 + chunks + 最近對話
- **Prompt 模式**：一般模式、HR 視角、技術面試官視角 — 針對不同任務有專屬 prompt
- **Token 成本控制**：追蹤用量、context trimming、top-K retrieval 限制輸入量
- **對話系統**：每份履歷可建多個 conversation session，messages 記錄 role/content/citations/token_usage

## Data Schema

### Resumes（履歷主表）
- id, original_text, created_at

### Resume Analysis（分析結果）
- summary, education_background, recommended_roles, suggestions

### Resume Chunks（RAG 切片）
- section_name (education / experience / project), content, chunk_index

### Conversations（對話主表）
- 每份履歷可建立多個對話 session

### Messages（對話訊息）
- role (user / assistant), content, citations, token_usage

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, React |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| Cache | Redis |
| Vector DB | Chroma |
| AI | OpenAI / Claude |
| Deploy | Docker (docker-compose) |

## Development Methodology

- BDD 定義使用者行為場景
- TDD 驅動核心模組開發

## Notes

- 前端 UI 基於 Figma Make 產出的 code 重構
- 詳細功能規格與資料 schema 請參考根目錄 README.md
