# ResumeCopilot 2.0 — Frontend

AI 履歷分析與互動式問答工具的前端介面，基於 Figma Make 產出的 UI 重構為 Next.js 應用。

## Tech Stack

| 技術 | 版本 |
|------|------|
| Next.js | 16.2.2 |
| React | 19.2.4 |
| TypeScript | 5.x |
| Tailwind CSS | 4.x |
| UI 元件 | Radix UI + shadcn/ui |
| Icons | Lucide React |
| Markdown 渲染 | react-markdown + remark-gfm |
| Typography | @tailwindcss/typography |

## 專案結構

```
src/
├── app/
│   ├── globals.css          # 全域樣式與 Tailwind 主題變數
│   ├── layout.tsx           # Root layout (字體、metadata)
│   └── page.tsx             # 首頁（履歷分析主介面 + 狀態管理）
├── components/
│   ├── ui/                  # shadcn/ui 基礎元件
│   ├── AnalysisResults.tsx  # 履歷分析結果展示
│   ├── ChatInterface.tsx    # AI 對話介面（Streaming + Markdown）
│   ├── ResumeInput.tsx      # 履歷輸入/上傳（文字 + PDF）
│   └── SettingsPanel.tsx    # 分析模式切換 & Token 用量
└── lib/
    ├── api.ts               # API Client（所有後端呼叫 + 型別定義）
    └── utils.ts             # cn() 工具函式
```

## 頁面功能

### ResumeInput
- 文字貼上或檔案上傳 (.txt, .doc, .docx, .pdf)
- PDF 上傳走後端 API（pypdf 解析），非 PDF 用 FileReader 讀取
- 分析後可收合/展開編輯，顯示上傳的檔案名稱

### AnalysisResults
- 履歷摘要 (Summary)
- 教育背景 (Education Background) — key-value 格式渲染
- 推薦職位 (Recommended Job Roles) — Badge 標籤
- 優化建議 (Improvement Suggestions)

### ChatInterface
- 針對分析結果的多輪對話
- **SSE Streaming** — AI 回覆逐字顯示，像 ChatGPT 的打字效果
- **Stop 按鈕** — 可中斷 streaming，已收到的文字保留
- **Typing 動畫** — 等待 AI 回覆時顯示跳動的三個點
- **Markdown 渲染** — AI 回覆支援粗體、列表、表格、code block
- **Citations** — 顯示 AI 引用了哪些履歷段落
- **Shift+Enter 換行** — 對話輸入框支援多行輸入
- 分析完成後才啟用

### SettingsPanel（右側欄）
- 分析模式切換：General / HR Perspective / Technical Perspective
- 切換 mode 會清空分析和對話，重新分析
- Token 使用量與預估成本即時顯示

## API Client（src/lib/api.ts）

所有後端 API 呼叫集中管理，TypeScript 型別對齊後端 Pydantic Schema：

| 函式 | 對應 API | 用途 |
|------|----------|------|
| `createResume()` | POST /resumes/ | 上傳純文字履歷 |
| `uploadResumePdf()` | POST /resumes/upload-pdf | 上傳 PDF |
| `createAnalysis()` | POST /resumes/{id}/analysis/ | 觸發 AI 分析 |
| `getAnalysis()` | GET /resumes/{id}/analysis/{mode} | 取得分析結果 |
| `createConversation()` | POST /conversations/ | 建立對話 session |
| `sendMessageStream()` | POST /messages/stream | Streaming 送訊息（SSE） |

### Streaming 架構

```
sendMessageStream()
  → fetch POST /messages/stream
  → ReadableStream reader.read() loop
  → 解析 SSE events:
      event: citations → 設定 citations
      event: token     → append 到 assistant message content
      event: done      → 更新 message_id + token_usage
  → AbortController.abort() 可中斷（Stop 按鈕）
```

## Getting Started

```bash
# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
```

開啟 http://localhost:3000 查看。

需要後端同時運行：`cd ../resumeCopilot2-backend && uvicorn app.main:app --reload --port 8000`

## 目前狀態

- [x] UI 介面完成（基於 Figma Make 重構）
- [x] 串接後端 API（API Client + 型別對齊）
- [x] PDF 上傳走後端 API 解析
- [x] AI 回覆 Markdown 渲染
- [x] SSE Streaming 逐字顯示 + Stop 按鈕
- [x] Typing 動畫（等待 AI 回覆）
- [x] Shift+Enter 換行
- [x] 409 重複分析自動 fallback
- [x] 錯誤處理與 loading 狀態
- [ ] GCP 部署（Dockerfile）

## 對應後端

後端 API 位於 `../resumeCopilot2-backend/`（FastAPI），詳見後端 README。
