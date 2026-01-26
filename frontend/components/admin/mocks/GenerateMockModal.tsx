"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Info, CheckCircle2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import type { MockBlueprint, MockGenerateResponse } from "@/lib/api/adminMocks";
import { adminMocksAPI } from "@/lib/api/adminMocks";
import { notify } from "@/lib/notify";

interface GenerateMockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  blueprint: MockBlueprint;
  onSuccess: () => void;
}

export function GenerateMockModal({
  open,
  onOpenChange,
  blueprint,
  onSuccess,
}: GenerateMockModalProps) {
  const router = useRouter();
  const [seed, setSeed] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [confirmationPhrase, setConfirmationPhrase] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<MockGenerateResponse | null>(null);

  const phraseMatches = confirmationPhrase.trim().toUpperCase() === "GENERATE MOCK";
  const canGenerate = phraseMatches && reason.trim().length >= 10 && !isGenerating;

  const handleGenerate = async () => {
    if (!canGenerate) return;

    setIsGenerating(true);
    try {
      const response = await adminMocksAPI.generateMock(blueprint.id, {
        seed: seed || undefined,
        reason,
        confirmation_phrase: confirmationPhrase,
      });
      setResult(response);
      notify.success(
        "Mock generated",
        `Generated ${response.generated_question_count} questions with seed ${response.seed}`,
      );
      onSuccess();
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to generate mock", err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleClose = () => {
    if (!isGenerating) {
      setSeed(null);
      setReason("");
      setConfirmationPhrase("");
      setResult(null);
      onOpenChange(false);
    }
  };

  if (result) {
    return (
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mock Generated Successfully</DialogTitle>
            <DialogDescription>Generation completed with the following details</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-muted-foreground">Run ID</Label>
                <p className="font-mono text-sm">{result.run_id}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Instance ID</Label>
                <p className="font-mono text-sm">{result.mock_instance_id}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Seed</Label>
                <p className="font-mono text-sm">{result.seed}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Questions Generated</Label>
                <p className="font-mono text-sm">{result.generated_question_count}</p>
              </div>
            </div>

            {result.warnings.length > 0 && (
              <div>
                <Label className="text-muted-foreground">Warnings</Label>
                <div className="mt-2 space-y-1">
                  {result.warnings.map((warning, idx) => (
                    <Alert key={idx} variant="default">
                      <AlertDescription>
                        <pre className="text-xs">{JSON.stringify(warning, null, 2)}</pre>
                      </AlertDescription>
                    </Alert>
                  ))}
                </div>
              </div>
            )}

            <Button
              onClick={() => {
                handleClose();
                // Switch to Instances tab and the instance will be visible there
                router.push("/admin/mocks?tab=instances");
                onSuccess();
              }}
              className="w-full"
            >
              View Instance
            </Button>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generate Mock Instance</DialogTitle>
          <DialogDescription>
            Generate a mock exam paper from "{blueprint.title}"
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>Deterministic Generation:</strong> Same seed + same blueprint = same paper.
              Leave seed empty for random generation.
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="seed">Seed (optional)</Label>
            <Input
              id="seed"
              type="number"
              placeholder="Auto-generate if empty"
              value={seed || ""}
              onChange={(e) => setSeed(e.target.value ? parseInt(e.target.value) : null)}
              disabled={isGenerating}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="reason">
              Reason <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="reason"
              placeholder="Explain why you are generating this mock (minimum 10 characters)..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              disabled={isGenerating}
              className={reason.length > 0 && reason.length < 10 ? "border-destructive" : ""}
            />
            {reason.length > 0 && reason.length < 10 && (
              <p className="text-sm text-destructive">Reason must be at least 10 characters</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmation-phrase">
              Type confirmation phrase <span className="text-destructive">*</span>
            </Label>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>Required phrase:</span>
                <code className="px-2 py-1 bg-muted rounded font-mono">GENERATE MOCK</code>
              </div>
              <Input
                id="confirmation-phrase"
                value={confirmationPhrase}
                onChange={(e) => setConfirmationPhrase(e.target.value)}
                placeholder="Type the phrase above..."
                disabled={isGenerating}
                className={confirmationPhrase && !phraseMatches ? "border-destructive" : ""}
              />
              <div className="flex items-center gap-2">
                {phraseMatches ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <Badge variant="default" className="text-xs bg-green-600">
                      Confirmed
                    </Badge>
                  </>
                ) : (
                  <>
                    <XCircle className="h-4 w-4 text-destructive" />
                    <Badge variant="destructive" className="text-xs">
                      Not confirmed
                    </Badge>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isGenerating}>
            Cancel
          </Button>
          <Button onClick={handleGenerate} disabled={!canGenerate || isGenerating}>
            {isGenerating ? "Generating..." : "Generate"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
