"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Database, Play, RefreshCw } from "lucide-react";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import type { WarehouseRuntimeStatus } from "@/lib/api/adminWarehouse";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ExportControlsCardProps {
  data: WarehouseRuntimeStatus | null;
  loading: boolean;
  onRunIncremental: (reason: string, phrase: string) => Promise<void>;
  onRunBackfill: (dataset: string, rangeStart: string, rangeEnd: string, reason: string, phrase: string) => Promise<void>;
}

const EXPORT_PHRASES = {
  incremental: "RUN WAREHOUSE EXPORT",
  backfill: "RUN WAREHOUSE BACKFILL",
};

const DATASETS = [
  { value: "attempts", label: "Attempts" },
  { value: "events", label: "Events" },
  { value: "mastery", label: "Mastery" },
  { value: "revision_queue", label: "Revision Queue" },
];

export function ExportControlsCard({
  data,
  loading,
  onRunIncremental,
  onRunBackfill,
}: ExportControlsCardProps) {
  const [showIncrementalModal, setShowIncrementalModal] = useState(false);
  const [showBackfillModal, setShowBackfillModal] = useState(false);
  const [incrementalReason, setIncrementalReason] = useState("");
  const [backfillReason, setBackfillReason] = useState("");
  const [backfillDataset, setBackfillDataset] = useState("attempts");
  const [backfillRangeStart, setBackfillRangeStart] = useState("");
  const [backfillRangeEnd, setBackfillRangeEnd] = useState("");
  const [showBackfillConfirm, setShowBackfillConfirm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isDisabled = data?.requested_mode === "disabled" || data?.warehouse_freeze || false;

  const handleIncremental = async () => {
    setIsSubmitting(true);
    try {
      await onRunIncremental(incrementalReason, EXPORT_PHRASES.incremental);
      setShowIncrementalModal(false);
      setIncrementalReason("");
    } catch (error) {
      // Error handled by parent
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackfill = async () => {
    setIsSubmitting(true);
    try {
      await onRunBackfill(
        backfillDataset,
        backfillRangeStart,
        backfillRangeEnd,
        backfillReason,
        EXPORT_PHRASES.backfill
      );
      setShowBackfillModal(false);
      setShowBackfillConfirm(false);
      setBackfillReason("");
      setBackfillRangeStart("");
      setBackfillRangeEnd("");
    } catch (error) {
      // Error handled by parent
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Export Controls
          </CardTitle>
          <CardDescription>Trigger warehouse exports</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <Button
              onClick={() => setShowIncrementalModal(true)}
              disabled={loading || isDisabled}
              className="flex items-center gap-2"
            >
              <Play className="h-4 w-4" />
              Run Incremental Export
            </Button>
            <Button
              onClick={() => setShowBackfillModal(true)}
              disabled={loading || isDisabled}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Database className="h-4 w-4" />
              Run Backfill Export
            </Button>
          </div>
          {isDisabled && (
            <p className="text-xs text-muted-foreground">
              {data?.warehouse_freeze
                ? "Warehouse is frozen. Unfreeze to run exports."
                : "Warehouse is disabled. Enable to run exports."}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Incremental Export Modal */}
      {showIncrementalModal && (
        <PoliceConfirmModal
          open={true}
          onOpenChange={setShowIncrementalModal}
          actionTitle="Run Incremental Export"
          requiredPhrase={EXPORT_PHRASES.incremental}
          reason={incrementalReason}
          onReasonChange={setIncrementalReason}
          onConfirm={handleIncremental}
          isSubmitting={isSubmitting}
        />
      )}

      {/* Backfill Export Modal - Two-step: first dialog, then police confirm */}
      {showBackfillModal && !showBackfillConfirm && (
        <Dialog open={true} onOpenChange={setShowBackfillModal}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Run Backfill Export</DialogTitle>
              <DialogDescription>
                Export historical data for a specific dataset and date range
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="backfill-dataset">Dataset</Label>
                <Select value={backfillDataset} onValueChange={setBackfillDataset}>
                  <SelectTrigger id="backfill-dataset">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DATASETS.map((ds) => (
                      <SelectItem key={ds.value} value={ds.value}>
                        {ds.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="backfill-range-start">Range Start (YYYY-MM-DD)</Label>
                <Input
                  id="backfill-range-start"
                  type="date"
                  value={backfillRangeStart}
                  onChange={(e) => setBackfillRangeStart(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="backfill-range-end">Range End (YYYY-MM-DD)</Label>
                <Input
                  id="backfill-range-end"
                  type="date"
                  value={backfillRangeEnd}
                  onChange={(e) => setBackfillRangeEnd(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowBackfillModal(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (backfillRangeStart && backfillRangeEnd) {
                    setShowBackfillModal(false);
                    setShowBackfillConfirm(true);
                  }
                }}
                disabled={!backfillRangeStart || !backfillRangeEnd}
              >
                Continue
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Police Confirm for Backfill */}
      {showBackfillConfirm && (
        <PoliceConfirmModal
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setShowBackfillConfirm(false);
              setBackfillReason("");
              setBackfillRangeStart("");
              setBackfillRangeEnd("");
            }
          }}
          actionTitle={`Run Backfill Export (${backfillDataset}, ${backfillRangeStart} to ${backfillRangeEnd})`}
          requiredPhrase={EXPORT_PHRASES.backfill}
          reason={backfillReason}
          onReasonChange={setBackfillReason}
          onConfirm={handleBackfill}
          isSubmitting={isSubmitting}
        />
      )}
    </>
  );
}
