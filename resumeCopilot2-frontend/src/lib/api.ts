/**
 * API Client — 所有後端 API 呼叫集中在這裡管理。
 *
 * 後端 Base URL: http://localhost:8000/api/v1
 * 每個函式對應一個後端 endpoint，回傳型別跟後端 Schema 對齊。
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL
  ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
  : "http://localhost:8000/api/v1";

// ---------- 型別定義（對齊後端 Pydantic Schema） ----------

/** 後端回傳的履歷資料 */
export interface ResumeResponse {
  id: string;
  original_text: string;
  file_name: string | null;
  created_at: string;
}

/** 後端回傳的分析結果 */
export interface AnalysisResponse {
  id: string;
  resume_id: string;
  mode: string;
  summary: string;
  education_background: Record<string, string>;
  recommended_roles: string[];
  suggestions: string[];
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  } | null;
  created_at: string;
}

/** 後端回傳的單則訊息 */
export interface MessageResponse {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations:
    | { section_name: string; chunk_index: number; content_preview: string }[]
    | null;
  token_usage: {
    estimated_prompt_tokens: number;
    estimated_completion_tokens: number;
  } | null;
  created_at: string;
}

/** 後端回傳的對話 session */
export interface ConversationResponse {
  id: string;
  resume_id: string;
  created_at: string;
  messages: MessageResponse[];
}

// ---------- 共用 fetch helper ----------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ---------- Resume 履歷 ----------

/** 上傳純文字履歷 */
export function createResume(text: string) {
  return apiFetch<ResumeResponse>("/resumes/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original_text: text }),
  });
}

/** 上傳 PDF 履歷 */
export function uploadResumePdf(file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<ResumeResponse>("/resumes/upload-pdf", {
    method: "POST",
    body: form,
  });
}

/** 列出所有履歷 */
export function listResumes() {
  return apiFetch<ResumeResponse[]>("/resumes/");
}

/** 取得單一履歷 */
export function getResume(id: string) {
  return apiFetch<ResumeResponse>(`/resumes/${id}`);
}

/** 刪除履歷 */
export function deleteResume(id: string) {
  return apiFetch<void>(`/resumes/${id}`, { method: "DELETE" });
}

// ---------- Analysis 分析 ----------

/** 觸發 AI 分析（指定 mode） */
export function createAnalysis(resumeId: string, mode: string) {
  return apiFetch<AnalysisResponse>(`/resumes/${resumeId}/analysis/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
}

/** 列出某份履歷的所有分析結果 */
export function listAnalyses(resumeId: string) {
  return apiFetch<AnalysisResponse[]>(`/resumes/${resumeId}/analysis/`);
}

/** 取得某份履歷特定 mode 的分析結果 */
export function getAnalysis(resumeId: string, mode: string) {
  return apiFetch<AnalysisResponse>(`/resumes/${resumeId}/analysis/${mode}`);
}

// ---------- Conversation 對話 ----------

/** 建立對話 session */
export function createConversation(resumeId: string) {
  return apiFetch<ConversationResponse>(
    `/resumes/${resumeId}/conversations/`,
    { method: "POST" }
  );
}

/** 列出某份履歷的所有對話 */
export function listConversations(resumeId: string) {
  return apiFetch<ConversationResponse[]>(
    `/resumes/${resumeId}/conversations/`
  );
}

/** 送出訊息（回傳 assistant 的回覆） */
export function sendMessage(
  resumeId: string,
  conversationId: string,
  content: string,
  mode: string
) {
  return apiFetch<MessageResponse>(
    `/resumes/${resumeId}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, mode }),
    }
  );
}

/** 取得對話歷史 */
export function getMessages(resumeId: string, conversationId: string) {
  return apiFetch<MessageResponse[]>(
    `/resumes/${resumeId}/conversations/${conversationId}/messages`
  );
}

// ---------- Streaming 對話 ----------

/** SSE 事件的 callback 型別 */
export interface StreamCallbacks {
  onToken: (token: string) => void;
  onCitations: (citations: MessageResponse["citations"]) => void;
  onDone: (data: { message_id: string; token_usage: MessageResponse["token_usage"] }) => void;
  onError: (error: Error) => void;
}

/**
 * Streaming 版送訊息 — 用 SSE 逐 token 接收 AI 回覆。
 * 回傳 AbortController 讓呼叫端可以中斷 stream（Stop 按鈕用）。
 */
export function sendMessageStream(
  resumeId: string,
  conversationId: string,
  content: string,
  mode: string,
  callbacks: StreamCallbacks
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(
        `${BASE_URL}/resumes/${resumeId}/conversations/${conversationId}/messages/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, mode }),
          signal: controller.signal,
        }
      );

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`API ${res.status}: ${body}`);
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE：每個事件以 \n\n 結尾
        const parts = buffer.split("\n\n");
        buffer = parts.pop()!; // 最後一段可能不完整，留著

        for (const part of parts) {
          if (!part.trim()) continue;

          const lines = part.split("\n");
          let eventType = "";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7);
            } else if (line.startsWith("data: ")) {
              data = line.slice(6);
            }
          }

          if (eventType === "token") {
            callbacks.onToken(JSON.parse(data));
          } else if (eventType === "citations") {
            callbacks.onCitations(JSON.parse(data));
          } else if (eventType === "done") {
            callbacks.onDone(JSON.parse(data));
          }
        }
      }
    } catch (err) {
      // AbortError 代表使用者主動中斷，不算錯誤
      if (err instanceof DOMException && err.name === "AbortError") return;
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}
