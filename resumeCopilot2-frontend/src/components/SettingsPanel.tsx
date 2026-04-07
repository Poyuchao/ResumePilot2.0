"use client";

import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";
import { Badge } from "./ui/badge";

interface SettingsPanelProps {
  mode: "general" | "hr" | "technical";
  onModeChange: (mode: "general" | "hr" | "technical") => void;
  tokensUsed: number;
  estimatedCost: number;
}

export function SettingsPanel({
  mode,
  onModeChange,
  tokensUsed,
  estimatedCost,
}: SettingsPanelProps) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Analysis Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <RadioGroup value={mode} onValueChange={onModeChange}>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="general" id="general" />
                <Label htmlFor="general" className="cursor-pointer font-normal">
                  General
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="hr" id="hr" />
                <Label htmlFor="hr" className="cursor-pointer font-normal">
                  HR Perspective
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="technical" id="technical" />
                <Label htmlFor="technical" className="cursor-pointer font-normal">
                  Technical Perspective
                </Label>
              </div>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Token Usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Tokens Used</span>
            <Badge variant="secondary">{tokensUsed.toLocaleString()}</Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Estimated Cost</span>
            <Badge variant="secondary">${estimatedCost.toFixed(4)}</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
