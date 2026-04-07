"use client";

import { GraduationCap, Briefcase, Lightbulb, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import type { AnalysisResponse } from "@/lib/api";

interface AnalysisResultsProps {
  data: AnalysisResponse | null;
}

export function AnalysisResults({ data }: AnalysisResultsProps) {
  if (!data) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <FileText className="size-12 mx-auto mb-4 opacity-20" />
        <p>Upload or paste your resume and click &quot;Analyze Resume&quot; to get started</p>
      </div>
    );
  }

  // education_background 從後端回來是 dict，例如 {school, major, degree}
  const edu = data.education_background;

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Analysis Results</h2>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileText className="size-5" />
              Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{data.summary}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <GraduationCap className="size-5" />
              Education Background
            </CardTitle>
          </CardHeader>
          <CardContent>
            {edu && Object.keys(edu).length > 0 ? (
              <div className="space-y-1">
                {Object.entries(edu).map(([key, value]) => (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="text-muted-foreground capitalize min-w-[60px]">
                      {key}:
                    </span>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No education data</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Briefcase className="size-5" />
              Recommended Job Roles
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {data.recommended_roles.map((role, index) => (
                <Badge key={index} variant="secondary" className="text-sm">
                  {role}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Lightbulb className="size-5" />
              Improvement Suggestions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.suggestions.map((suggestion, index) => (
                <li key={index} className="flex gap-2 text-sm">
                  <span className="text-primary mt-0.5">•</span>
                  <span className="flex-1">{suggestion}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
