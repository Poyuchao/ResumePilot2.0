"use client";

import { Upload, Sparkles, ChevronDown, ChevronUp, Edit } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Card, CardContent } from "./ui/card";
import { useState } from "react";

interface ResumeInputProps {
  resume: string;
  onResumeChange: (value: string) => void;
  onAnalyze: () => void;
  onFileUpload: (file: File) => void;
  isAnalyzing: boolean;
  isAnalyzed: boolean;
  fileName: string | null;
}

export function ResumeInput({
  resume,
  onResumeChange,
  onAnalyze,
  onFileUpload,
  isAnalyzing,
  isAnalyzed,
  fileName,
}: ResumeInputProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type === "application/pdf") {
        // PDF 走後端 API 解析
        onFileUpload(file);
      } else {
        // 非 PDF（txt 等）用 FileReader 讀取文字
        const reader = new FileReader();
        reader.onload = (event) => {
          const text = event.target?.result as string;
          onResumeChange(text);
        };
        reader.readAsText(file);
      }
    }
  };

  if (isAnalyzed && !isExpanded) {
    return (
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-semibold">Resume Content</h3>
                <span className="text-xs text-muted-foreground">
                  {fileName
                    ? `(${fileName})`
                    : `(${resume.length} characters)`}
                </span>
              </div>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {resume}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsExpanded(true)}
              >
                <Edit className="mr-2 size-4" />
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(true)}
              >
                <ChevronDown className="size-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Resume Input</h2>
        <div className="flex items-center gap-2">
          {isAnalyzed && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(false)}
            >
              <ChevronUp className="size-4" />
            </Button>
          )}
          <label>
            <input
              type="file"
              accept=".txt,.doc,.docx,.pdf"
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button variant="outline" size="sm" asChild>
              <span className="cursor-pointer">
                <Upload className="mr-2 size-4" />
                Upload File
              </span>
            </Button>
          </label>
        </div>
      </div>

      <Textarea
        placeholder="Paste your resume content here..."
        value={resume}
        onChange={(e) => onResumeChange(e.target.value)}
        className="min-h-[200px] resize-none"
      />

      <Button
        onClick={onAnalyze}
        disabled={!resume.trim() || isAnalyzing}
        className="w-full"
        size="lg"
      >
        <Sparkles className="mr-2 size-5" />
        {isAnalyzing ? "Analyzing..." : isAnalyzed ? "Re-analyze Resume" : "Analyze Resume"}
      </Button>
    </div>
  );
}
