"use client";

import { useState, useRef, useCallback } from "react";
import { ResumeInput } from "@/components/ResumeInput";
import { AnalysisResults } from "@/components/AnalysisResults";
import { ChatInterface } from "@/components/ChatInterface";
import { SettingsPanel } from "@/components/SettingsPanel";
import { Separator } from "@/components/ui/separator";
import { Brain } from "lucide-react";
import {
  createResume,
  uploadResumePdf,
  createAnalysis,
  createConversation,
  sendMessageStream,
  type AnalysisResponse,
  type MessageResponse,
} from "@/lib/api";

export default function Home() {
  // 履歷狀態
  const [resume, setResume] = useState("");
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // 分析狀態
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // 對話狀態
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  // Streaming 中斷用的 AbortController ref
  const abortRef = useRef<AbortController | null>(null);

  // 設定
  const [mode, setMode] = useState<"general" | "hr" | "technical">("general");
  const [tokensUsed, setTokensUsed] = useState(0);
  const [estimatedCost, setEstimatedCost] = useState(0);

  // 切換 mode 時清空舊分析與對話，讓使用者重新分析
  const handleModeChange = (newMode: "general" | "hr" | "technical") => {
    setMode(newMode);
    setAnalysisData(null);
    setMessages([]);
    setConversationId(null);
    setAnalysisError(null);
  };

  /** 上傳 PDF — 走後端 API，回傳 resumeId + 解析出的文字 */
  const handleFileUpload = async (file: File) => {
    try {
      const res = await uploadResumePdf(file);
      setResumeId(res.id);
      setResume(res.original_text);
      setFileName(res.file_name);
      setAnalysisData(null);
      setMessages([]);
      setConversationId(null);
      setAnalysisError(null);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "PDF 上傳失敗");
    }
  };

  /** 分析履歷 */
  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      let id = resumeId;
      if (!id) {
        const res = await createResume(resume);
        id = res.id;
        setResumeId(id);
      }

      const analysis = await createAnalysis(id, mode);
      setAnalysisData(analysis);

      if (analysis.token_usage) {
        const tokens = analysis.token_usage.total_tokens;
        setTokensUsed((prev) => prev + tokens);
        setEstimatedCost((prev) => prev + tokens * 0.00001);
      }

      setMessages([]);
      setConversationId(null);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "分析失敗";
      if (msg.includes("409") && resumeId) {
        try {
          const { getAnalysis } = await import("@/lib/api");
          const existing = await getAnalysis(resumeId, mode);
          setAnalysisData(existing);
        } catch {
          setAnalysisError("無法取得先前的分析結果");
        }
      } else {
        setAnalysisError(msg);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  /** 送出對話訊息（Streaming 版） */
  const handleSendMessage = useCallback(async (content: string) => {
    if (!resumeId) return;
    setIsStreaming(true);

    // 樂觀更新：先顯示使用者訊息
    const userMsg: MessageResponse = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      citations: null,
      token_usage: null,
      created_at: new Date().toISOString(),
    };

    // 建立一個空的 assistant 訊息，準備接收 streaming tokens
    const streamingMsgId = crypto.randomUUID();
    const streamingMsg: MessageResponse = {
      id: streamingMsgId,
      role: "assistant",
      content: "",
      citations: null,
      token_usage: null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, streamingMsg]);

    try {
      // 確保有 conversation
      let cid = conversationId;
      if (!cid) {
        const conv = await createConversation(resumeId);
        cid = conv.id;
        setConversationId(cid);
      }

      // 開始 streaming
      const controller = sendMessageStream(resumeId, cid, content, mode, {
        onToken: (token) => {
          // 每收到一個 token，就更新最後一則 assistant 訊息
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMsgId
                ? { ...msg, content: msg.content + token }
                : msg
            )
          );
        },
        onCitations: (citations) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMsgId ? { ...msg, citations } : msg
            )
          );
        },
        onDone: (data) => {
          // Stream 完成：更新 message_id 和 token_usage
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMsgId
                ? { ...msg, id: data.message_id, token_usage: data.token_usage }
                : msg
            )
          );

          if (data.token_usage) {
            const tokens =
              data.token_usage.estimated_prompt_tokens +
              data.token_usage.estimated_completion_tokens;
            setTokensUsed((prev) => prev + tokens);
            setEstimatedCost((prev) => prev + tokens * 0.00001);
          }

          setIsStreaming(false);
          abortRef.current = null;
        },
        onError: (error) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === streamingMsgId
                ? { ...msg, content: msg.content || `Error: ${error.message}` }
                : msg
            )
          );
          setIsStreaming(false);
          abortRef.current = null;
        },
      });

      abortRef.current = controller;
    } catch (err) {
      // createConversation 失敗等情況
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === streamingMsgId
            ? { ...msg, content: `Error: ${err instanceof Error ? err.message : "送出訊息失敗"}` }
            : msg
        )
      );
      setIsStreaming(false);
    }
  }, [resumeId, conversationId, mode]);

  /** 中斷 streaming */
  const handleStopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  return (
    <div className="h-screen w-full bg-background flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-lg bg-primary flex items-center justify-center">
            <Brain className="size-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold">AI Resume Copilot</h1>
            <p className="text-sm text-muted-foreground">
              Analyze and enhance your resume with AI assistance
            </p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Main Content Area */}
        <div className="flex-1 overflow-auto">
          <div className="max-w-4xl mx-auto p-6 space-y-8">
            <ResumeInput
              resume={resume}
              onResumeChange={(text) => {
                setResume(text);
                setResumeId(null);
                setFileName(null);
              }}
              onAnalyze={handleAnalyze}
              onFileUpload={handleFileUpload}
              isAnalyzing={isAnalyzing}
              isAnalyzed={!!analysisData}
              fileName={fileName}
            />

            {analysisError && (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
                {analysisError}
              </div>
            )}

            <Separator />

            <AnalysisResults data={analysisData} />

            {analysisData && (
              <>
                <Separator />

                <div className="min-h-[500px] flex flex-col">
                  <ChatInterface
                    messages={messages}
                    onSendMessage={handleSendMessage}
                    onStop={handleStopStreaming}
                    isEnabled={!!analysisData}
                    isStreaming={isStreaming}
                  />
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="w-80 border-l bg-muted/30 p-6 overflow-auto">
          <SettingsPanel
            mode={mode}
            onModeChange={handleModeChange}
            tokensUsed={tokensUsed}
            estimatedCost={estimatedCost}
          />
        </div>
      </div>
    </div>
  );
}
