/**
 * Review summary showing score and session metadata
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, XCircle, Clock } from "lucide-react";
import { format } from "date-fns";
import type { SessionMeta } from "@/lib/types/session";

interface ReviewSummaryProps {
  session: SessionMeta;
}

export function ReviewSummary({ session }: ReviewSummaryProps) {
  const scorePercent = session.score_pct || 0;
  const scoreCorrect = session.score_correct || 0;
  const scoreTotal = session.score_total || 0;
  const scoreIncorrect = scoreTotal - scoreCorrect;

  const getScoreColor = () => {
    if (scorePercent >= 80) return "text-green-600";
    if (scorePercent >= 60) return "text-amber-600";
    return "text-red-600";
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Session Results</CardTitle>
          <Badge variant={session.mode === "EXAM" ? "default" : "secondary"}>
            {session.mode}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Score Display */}
        <div className="text-center py-4">
          <div className={`text-5xl font-bold ${getScoreColor()}`}>
            {scorePercent.toFixed(1)}%
          </div>
          <p className="text-muted-foreground mt-2">
            {scoreCorrect} correct out of {scoreTotal} questions
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 rounded-lg border">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
            <div>
              <p className="text-sm text-muted-foreground">Correct</p>
              <p className="text-2xl font-bold">{scoreCorrect}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 rounded-lg border">
            <XCircle className="h-8 w-8 text-red-600" />
            <div>
              <p className="text-sm text-muted-foreground">Incorrect</p>
              <p className="text-2xl font-bold">{scoreIncorrect}</p>
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div className="space-y-2 text-sm border-t pt-4">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Submitted:</span>
            <span className="font-medium">
              {session.submitted_at
                ? format(new Date(session.submitted_at), "MMM d, yyyy h:mm a")
                : "N/A"}
            </span>
          </div>
          {session.duration_seconds && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Duration:</span>
              <span className="font-medium flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {Math.floor(session.duration_seconds / 60)} minutes
              </span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status:</span>
            <Badge variant={session.status === "SUBMITTED" ? "default" : "secondary"}>
              {session.status}
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
