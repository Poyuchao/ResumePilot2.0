# ResumePilot 2.0 — Backend

AI 履歷分析與互動式問答工具的後端服務，使用 FastAPI + PostgreSQL + Chroma 向量資料庫。

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (Python 3.11) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (Docker) |
| Cache | Redis 7 (Docker) |
| Vector DB | Chroma (本地持久化, `./chroma_data/`) |
| Embedding | OpenAI `text-embedding-3-small` (1536 維) |
| LLM | OpenAI / Claude (可切換) |
| AI Framework | LangChain |
| PDF 解析 | pypdf |

## 快速啟動

```bash
# 1. 啟動 Docker (PostgreSQL + Redis)
docker compose up -d

# 2. 啟動 Python 虛擬環境
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # Mac/Linux

# 3. 啟動 FastAPI server
uvicorn app.main:app --reload --port 8000

# 4. 開瀏覽器
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```

## 專案結構

```
app/
├── main.py                  # FastAPI 入口，啟動 + create_all
├── config.py                # 環境變數設定 (pydantic-settings)
├── db/
│   ├── database.py          # SQLAlchemy async engine + session
│   └── redis.py             # Redis 連線
├── models/                  # ORM Models (對應 DB tables)
│   ├── resume.py            # Resume, ResumeChunk
│   ├── analysis.py          # ResumeAnalysis
│   └── conversation.py      # Conversation, Message
├── schemas/                 # Pydantic Schemas (API 請求/回應格式)
│   ├── resume.py
│   ├── analysis.py
│   └── conversation.py
├── services/                # 商業邏輯層
│   ├── resume_service.py    # 履歷 CRUD + chunks 存取
│   ├── analysis_service.py  # AI 分析（3 種 mode）
│   ├── pdf_service.py       # PDF → 純文字
│   ├── chunking_service.py  # Section-based chunking
│   ├── llm_service.py       # LangChain LLM 初始化
│   ├── rag_service.py       # RAG chain 組裝
│   └── vectorstore_service.py # Chroma 向量存取
└── api/v1/                  # API Routes
    ├── router.py            # 路由總管
    ├── resumes.py           # 履歷 CRUD + PDF 上傳
    ├── analysis.py          # AI 分析
    └── conversations.py     # 對話系統
```

## Database Schema

5 張 tables，關係如下：

```
resumes (履歷主表)
├── resume_chunks (RAG 切片，1 對多)
├── resume_analyses (AI 分析結果，1 對多，每個 mode 一筆)
└── conversations (對話 session，1 對多)
    └── messages (對話訊息，1 對多)
```

### resumes
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| original_text | TEXT | 履歷全文 |
| file_name | VARCHAR(255) | PDF 上傳時的原始檔名 (nullable) |
| created_at | TIMESTAMPTZ | 建立時間 |

### resume_chunks
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| resume_id | UUID | FK → resumes |
| section_name | VARCHAR(50) | header / skills / experience / education / project |
| content | TEXT | 該段落的文字 |
| chunk_index | INTEGER | 同 section 內的流水號 |

### resume_analyses
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| resume_id | UUID | FK → resumes |
| mode | VARCHAR(20) | general / hr / technical |
| summary | TEXT | 履歷摘要 |
| education_background | JSON | 學歷資訊 |
| recommended_roles | JSON | 推薦職位 |
| suggestions | JSON | 改善建議 |
| token_usage | JSON | LLM token 用量 |

## API Endpoints

### Resume CRUD + PDF 上傳

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| POST | `/api/v1/resumes/` | 上傳純文字履歷 | ✅ |
| POST | `/api/v1/resumes/upload-pdf` | 上傳 PDF 履歷 | ✅ |
| GET | `/api/v1/resumes/` | 列出所有履歷 | ✅ |
| GET | `/api/v1/resumes/{id}` | 取得單一履歷 | ✅ |
| DELETE | `/api/v1/resumes/{id}` | 刪除履歷 | ✅ |

### AI Analysis

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| POST | `/api/v1/resumes/{id}/analysis/` | 觸發分析 (body: mode) | ✅ |
| GET | `/api/v1/resumes/{id}/analysis/` | 列出所有分析結果 | ✅ |
| GET | `/api/v1/resumes/{id}/analysis/{mode}` | 取得特定 mode 結果 | ✅ |

### Conversations

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| POST | `/api/v1/resumes/{id}/conversations/` | 建立對話 session | ✅ |
| GET | `/api/v1/resumes/{id}/conversations/` | 列出對話 | ✅ |
| POST | `.../conversations/{cid}/messages` | 送出訊息 + AI 回覆 | ✅ |
| GET | `.../conversations/{cid}/messages` | 取得訊息歷史 | ✅ |

## 核心流程

### PDF 上傳 → Chunking → 向量存入

```
使用者上傳 PDF
    ↓
pypdf 提取文字 (pdf_service)
    ↓
存進 resumes table (resume_service)
    ↓
Section-based chunking (chunking_service)
  → 辨識: header / skills / experience / education / project
  → 超過 600 字的 section 會再細切
    ↓
┌──────────────────┬────────────────────┐
│  PostgreSQL       │  Chroma            │
│  resume_chunks    │  向量 + metadata    │
│  (原始紀錄備份)    │  (RAG 檢索用)       │
└──────────────────┴────────────────────┘
```

### AI Analysis (3 種 mode)

```
履歷全文 → Prompt (依 mode 切換角色) → LLM → JSON 回應 → 存 DB
```

- **general**: 專業履歷顧問，全面評估
- **hr**: 資深 HR 主管，招募者視角
- **technical**: 技術面試官，評估技術深度

### Conversation 對話系統 (RAG + 多輪對話)

```
使用者送出問題
    ↓
1. Chroma 搜尋相關 chunks（filter: resume_id，top-K=3）
    ↓
2. 撈最近 10 則對話歷史
    ↓
3. 組合 prompt: system(角色) + context(chunks) + history + question
    ↓
4. LLM 回答
    ↓
5. 儲存 user msg + assistant msg（含 citations + token_usage）
```

- **mode** 同樣支援 general / hr / technical，切換 AI 角色
- **citations**: 回傳用了哪些 chunks（section_name, chunk_index, content_preview）
- **token_usage**: 估算的 prompt/completion tokens
- 每份履歷可建多個 conversation session，每個 session 獨立對話歷史

## 環境變數 (.env)

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/resume_copilot
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=openai          # openai 或 claude
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=sk-ant-... # 如果用 claude
CLAUDE_MODEL=claude-sonnet-4-6
```

## 開發進度

- [x] FastAPI 架構 + 專案結構
- [x] Docker Compose (PostgreSQL + Redis)
- [x] DB Schema (5 tables + ORM models)
- [x] Resume CRUD API
- [x] LLM 串接 (OpenAI / Claude)
- [x] Analysis API (3 modes + token usage)
- [x] PDF 上傳 (pypdf 文字提取)
- [x] Section-based Chunking
- [x] Chroma 向量存入 (持久化)
- [x] Conversation 對話系統 (RAG + 多輪對話)
- [ ] 前後端串接
