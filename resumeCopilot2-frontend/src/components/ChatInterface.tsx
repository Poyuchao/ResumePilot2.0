"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Square, Bot, User, FileText } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { ScrollArea } from "./ui/scroll-area";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MessageResponse } from "@/lib/api";

interface ChatInterfaceProps {
  onSendMessage: (message: string) => void;
  onStop: () => void;
  messages: MessageResponse[];
  isEnabled: boolean;
  isStreaming?: boolean;
}

export function ChatInterface({
  onSendMessage,
  onStop,
  messages,
  isEnabled,
  isStreaming = false,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // 自動調整 textarea 高度
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (input.trim() && isEnabled && !isStreaming) {
      onSendMessage(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter = 送出，Shift+Enter = 換行
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-xl font-semibold">Chat with AI</h2>
        {!isEnabled && (
          <p className="text-sm text-muted-foreground mt-1">
            Analyze a resume first to start chatting
          </p>
        )}
      </div>

      <ScrollArea className="flex-1 pr-4" ref={scrollRef}>
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Bot className="size-12 mx-auto mb-4 opacity-20" />
              <p className="text-sm">
                Ask questions about the resume analysis...
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <div key={message.id}>
                <div
                  className={`flex gap-3 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="flex-shrink-0 size-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Bot className="size-4 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      !message.content && isStreaming ? (
                        <div className="flex items-center gap-1 py-1">
                          <span className="size-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:0ms]" />
                          <span className="size-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:150ms]" />
                          <span className="size-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:300ms]" />
                        </div>
                      ) : (
                        <div className="prose prose-sm dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      )
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    )}
                  </div>
                  {message.role === "user" && (
                    <div className="flex-shrink-0 size-8 rounded-full bg-primary flex items-center justify-center">
                      <User className="size-4 text-primary-foreground" />
                    </div>
                  )}
                </div>

                {/* Citations — 顯示 AI 回覆引用了哪些履歷段落 */}
                {message.citations && message.citations.length > 0 && (
                  <div className="ml-11 mt-1 space-y-1">
                    {message.citations.map((cite, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-1.5 text-xs text-muted-foreground"
                      >
                        <FileText className="size-3 mt-0.5 flex-shrink-0" />
                        <span>
                          <span className="font-medium capitalize">
                            {cite.section_name}
                          </span>
                          {cite.content_preview && (
                            <span className="ml-1">— {cite.content_preview}</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}

          {/* Streaming 時最後一則 assistant 訊息還是空的，顯示 cursor 動畫 */}
        </div>
      </ScrollArea>

      <div className="mt-4 flex gap-2 items-end">
        <Textarea
          ref={textareaRef}
          placeholder="Ask about your resume... (Shift+Enter to add new line)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!isEnabled || isStreaming}
          className="flex-1 min-h-[40px] max-h-[150px] resize-none"
          rows={1}
        />
        {isStreaming ? (
          <Button onClick={onStop} variant="destructive" className="h-10">
            <Square className="size-4" />
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            disabled={!input.trim() || !isEnabled}
            className="h-10"
          >
            <Send className="size-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
