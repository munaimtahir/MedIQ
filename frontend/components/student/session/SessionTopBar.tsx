/**
 * Session top bar with timer, progress, and submit button
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Clock, CheckCircle2 } from "lucide-react";
import type { SessionMode, SessionProgress } from "@/lib/types/session";
import { useCountdown } from "@/lib/hooks/useCountdown";

interface SessionTopBarProps {
  mode: SessionMode;
  expiresAt: string | null;
  progress: SessionProgress;
  totalQuestions: number;
  onSubmit: () => void;
  onExpire?: () => void;
}

export function SessionTopBar({
  mode,
  expiresAt,
  progress,
  totalQuestions,
  onSubmit,
  onExpire,
}: SessionTopBarProps) {
  const countdown = useCountdown(expiresAt, onExpire);

  const progressPercent = (progress.answered_count / totalQuestions) * 100;

  return (
    <div className="sticky top-0 z-10 border-b bg-background">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Mode & Progress */}
          <div className="flex min-w-0 flex-1 items-center gap-4">
            <Badge variant={mode === "EXAM" ? "default" : "secondary"}>
              {mode === "EXAM" ? "Exam Mode" : "Tutor Mode"}
            </Badge>

            <div className="hidden min-w-0 flex-1 items-center gap-2 text-sm text-muted-foreground sm:flex">
              <span className="whitespace-nowrap">
                {progress.answered_count}/{totalQuestions}
              </span>
              <Progress value={progressPercent} className="w-full max-w-[200px]" />
            </div>
          </div>

          {/* Center: Timer (if exists) */}
          {expiresAt && (
            <div
              className={`flex items-center gap-2 ${countdown.isWarning ? "text-amber-600" : ""}`}
            >
              <Clock className="h-4 w-4" />
              <span className="font-mono text-sm font-medium">{countdown.formattedTime}</span>
            </div>
          )}

          {/* Right: Submit Button */}
          <Button onClick={onSubmit} size="sm">
            <CheckCircle2 className="mr-2 h-4 w-4" />
            Submit
          </Button>
        </div>

        {/* Mobile Progress */}
        <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground sm:hidden">
          <span className="whitespace-nowrap">
            {progress.answered_count}/{totalQuestions}
          </span>
          <Progress value={progressPercent} className="flex-1" />
        </div>
      </div>
    </div>
  );
}
