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

## 專案結構

```
src/
├── app/
│   ├── globals.css          # 全域樣式與 Tailwind 主題變數
│   ├── layout.tsx           # Root layout (字體、metadata)
│   └── page.tsx             # 首頁（履歷分析主介面）
├── components/
│   ├── ui/                  # shadcn/ui 基礎元件
│   │   ├── badge.tsx
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── label.tsx
│   │   ├── radio-group.tsx
│   │   ├── scroll-area.tsx
│   │   ├── separator.tsx
│   │   └── textarea.tsx
│   ├── AnalysisResults.tsx  # 履歷分析結果展示
│   ├── ChatInterface.tsx    # AI 對話介面
│   ├── ResumeInput.tsx      # 履歷輸入/上傳
│   └── SettingsPanel.tsx    # 分析模式切換 & Token 用量
└── lib/
    └── utils.ts             # cn() 工具函式
```

## 頁面功能

### ResumeInput
- 文字貼上或檔案上傳 (.txt, .doc, .docx, .pdf)
- 分析後可收合/展開編輯

### AnalysisResults
- 履歷摘要 (Summary)
- 教育背景 (Education Background)
- 推薦職位 (Recommended Job Roles)
- 優化建議 (Improvement Suggestions)

### ChatInterface
- 針對分析結果的多輪對話
- 使用者/AI 訊息氣泡式呈現
- 分析完成後才啟用

### SettingsPanel（右側欄）
- 分析模式切換：General / HR Perspective / Technical Perspective
- Token 使用量與預估成本顯示

## Getting Started

```bash
# 安裝依賴
npm install

# 啟動開發伺服器
npm run dev
```

開啟 http://localhost:3000 查看。

## 目前狀態

- [x] UI 介面完成（基於 Figma Make 重構）
- [ ] 串接後端 API（目前使用 mock data）
- [ ] 履歷檔案解析（目前僅支援純文字讀取）

## 對應後端

後端 API 位於 `../resumeCopilot2-backend/`（FastAPI），待開發。
