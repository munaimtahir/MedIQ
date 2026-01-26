"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import { RANKING_COMPUTE_PHRASE, type RankingRuntimeResponse } from "@/lib/api/adminRanking";
import { Play } from "lucide-react";

interface ComputeCardProps {
  data: RankingRuntimeResponse | null;
  loading: boolean;
  onCompute: (payload: {
    mock_instance_id: string;
    cohort_id: string;
    reason: string;
    confirmation_phrase: string;
  }) => Promise<void>;
}

export function ComputeCard({ data, loading, onCompute }: ComputeCardProps) {
  const [showModal, setShowModal] = useState(false);
  const [reason, setReason] = useState("");
  const [mockInstanceId, setMockInstanceId] = useState("");
  const [cohortId, setCohortId] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const disabled =
    loading ||
    (data?.requested_mode === "disabled") ||
    (data?.freeze ?? false);

  const handleCompute = async () => {
    setIsSubmitting(true);
    try {
      await onCompute({
        mock_instance_id: mockInstanceId.trim(),
        cohort_id: cohortId.trim(),
        reason,
        confirmation_phrase: RANKING_COMPUTE_PHRASE,
      });
      setShowModal(false);
      setReason("");
    } catch {
      // parent handles toast
    } finally {
      setIsSubmitting(false);
    }
  };

  const canOpen =
    !disabled &&
    mockInstanceId.trim().length > 0 &&
    cohortId.trim().length > 0;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Manual Compute</CardTitle>
          <CardDescription>
            Run ranking for a mock instance + cohort. Requires police confirmation.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="ranking-mock-instance">mock_instance_id</Label>
            <Input
              id="ranking-mock-instance"
              placeholder="UUID"
              value={mockInstanceId}
              onChange={(e) => setMockInstanceId(e.target.value)}
              disabled={loading}
              className="font-mono"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ranking-cohort">cohort_id</Label>
            <Input
              id="ranking-cohort"
              placeholder="e.g. year:1:block:A"
              value={cohortId}
              onChange={(e) => setCohortId(e.target.value)}
              disabled={loading}
            />
          </div>
          <Button
            onClick={() => setShowModal(true)}
            disabled={!canOpen || disabled}
            className="gap-2"
          >
            <Play className="h-4 w-4" />
            Compute Ranking
          </Button>
        </CardContent>
      </Card>

      {showModal && (
        <PoliceConfirmModal
          open
          onOpenChange={(open) => !open && setShowModal(false)}
          actionTitle="Run Ranking Compute"
          requiredPhrase={RANKING_COMPUTE_PHRASE}
          reason={reason}
          onReasonChange={setReason}
          onConfirm={handleCompute}
          isSubmitting={isSubmitting}
        />
      )}
    </>
  );
}
