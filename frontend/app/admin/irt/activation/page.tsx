"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { ErrorState } from "@/components/status/ErrorState";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Power,
  PowerOff,
  Loader,
  RefreshCw,
  Shield,
} from "lucide-react";
import { formatDistanceToNow } from "@/lib/dateUtils";

interface ActivationStatus {
  flags: {
    active: boolean;
    scope: string;
    model: string;
    shadow: boolean;
  };
  latest_decision: {
    eligible: boolean | null;
    run_id: string | null;
    created_at: string | null;
  };
  recent_events: Array<{
    event_type: string;
    created_at: string;
    created_by: string;
    reason: string | null;
  }>;
}

interface GateResult {
  name: string;
  passed: boolean;
  value: number | null;
  threshold: number | null;
  notes: string;
}

interface EvaluationResult {
  decision: {
    eligible: boolean;
    policy_version: string;
    evaluated_at: string;
    recommended_scope: string;
    recommended_model: string;
  };
  eligible: boolean;
  gates: GateResult[];
}

export default function IrtActivationPage() {
  const [status, setStatus] = useState<ActivationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [activating, setActivating] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [showEvaluationModal, setShowEvaluationModal] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string>("");

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/irt/activation/status");
      if (!response.ok) throw new Error("Failed to load activation status");
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to load activation status:", err);
      setError(err instanceof Error ? err : new Error("Failed to load activation status"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleEvaluate = async () => {
    if (!selectedRunId) {
      alert("Please enter a run ID");
      return;
    }

    setEvaluating(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/irt/activation/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: selectedRunId,
          policy_version: "v1",
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || "Failed to evaluate activation");
      }

      const data = await response.json();
      setEvaluationResult(data);
      setShowEvaluationModal(true);
      await loadStatus(); // Refresh status
    } catch (err) {
      console.error("Failed to evaluate activation:", err);
      setError(err instanceof Error ? err : new Error("Failed to evaluate activation"));
    } finally {
      setEvaluating(false);
    }
  };

  const handleActivate = async () => {
    if (!evaluationResult?.eligible) {
      alert("Cannot activate: run is not eligible. All gates must pass.");
      return;
    }

    const reason = prompt("Enter reason for activation:");
    if (!reason) return;

    setActivating(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/irt/activation/activate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: selectedRunId,
          scope: evaluationResult.decision.recommended_scope,
          model_type: evaluationResult.decision.recommended_model,
          reason,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || "Failed to activate IRT");
      }

      alert("IRT activated successfully!");
      await loadStatus();
      setShowEvaluationModal(false);
    } catch (err) {
      console.error("Failed to activate IRT:", err);
      setError(err instanceof Error ? err : new Error("Failed to activate IRT"));
    } finally {
      setActivating(false);
    }
  };

  const handleDeactivate = async () => {
    const reason = prompt("Enter reason for deactivation:");
    if (!reason) return;

    if (!confirm("Are you sure you want to deactivate IRT? This will immediately disable IRT for all student-facing decisions.")) {
      return;
    }

    setDeactivating(true);
    setError(null);
    try {
      const response = await fetch("/api/admin/irt/activation/deactivate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || "Failed to deactivate IRT");
      }

      alert("IRT deactivated successfully!");
      await loadStatus();
    } catch (err) {
      console.error("Failed to deactivate IRT:", err);
      setError(err instanceof Error ? err : new Error("Failed to deactivate IRT"));
    } finally {
      setDeactivating(false);
    }
  };

  const getScopeBadge = (scope: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      none: "secondary",
      shadow_only: "outline",
      selection_only: "default",
      scoring_only: "default",
      selection_and_scoring: "default",
    };
    return <Badge variant={variants[scope] || "secondary"}>{scope}</Badge>;
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">IRT Activation</h1>
        <SkeletonTable rows={3} cols={4} />
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="container mx-auto py-8">
        <h1 className="text-3xl font-bold mb-6">IRT Activation</h1>
        <ErrorState
          title="Failed to load activation status"
          description={error?.message}
          onAction={loadStatus}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">IRT Activation</h1>
          <p className="text-muted-foreground mt-2">
            Manage IRT activation for student-facing decisions. All gates must pass before activation.
          </p>
        </div>
        <Button variant="outline" onClick={loadStatus} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      )}

      {/* Current Status */}
      {status && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Current Status
              {status.flags.active ? (
                <Badge variant="default" className="bg-green-600">
                  <Power className="h-3 w-3 mr-1" />
                  Active
                </Badge>
              ) : (
                <Badge variant="secondary">
                  <PowerOff className="h-3 w-3 mr-1" />
                  Inactive
                </Badge>
              )}
            </CardTitle>
            <CardDescription>IRT activation flags and latest decision</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Active</p>
                <p className="text-lg font-semibold">{status.flags.active ? "Yes" : "No"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Scope</p>
                <div className="mt-1">{getScopeBadge(status.flags.scope)}</div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Model</p>
                <p className="text-lg font-semibold">{status.flags.model}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Shadow</p>
                <p className="text-lg font-semibold">{status.flags.shadow ? "Enabled" : "Disabled"}</p>
              </div>
            </div>

            {status.latest_decision.eligible !== null && (
              <div className="pt-4 border-t">
                <p className="text-sm font-semibold mb-2">Latest Decision</p>
                <div className="flex items-center gap-2">
                  {status.latest_decision.eligible ? (
                    <>
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span className="text-sm">Eligible for activation</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-red-600" />
                      <span className="text-sm">Not eligible (gates failed)</span>
                    </>
                  )}
                  {status.latest_decision.created_at && (
                    <span className="text-xs text-muted-foreground ml-2">
                      {formatDistanceToNow(new Date(status.latest_decision.created_at), { addSuffix: true })}
                    </span>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Evaluation */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Evaluate Activation Gates</CardTitle>
          <CardDescription>
            Evaluate a calibration run against all 6 activation gates. All gates must pass for eligibility.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter calibration run ID (UUID)"
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="flex-1 px-3 py-2 border rounded-md"
            />
            <Button onClick={handleEvaluate} disabled={evaluating || !selectedRunId}>
              {evaluating ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <Shield className="h-4 w-4 mr-2" />
                  Evaluate
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Actions</CardTitle>
          <CardDescription>Activate or deactivate IRT for student-facing decisions</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button
              onClick={handleActivate}
              disabled={activating || !evaluationResult?.eligible || status?.flags.active}
              variant="default"
            >
              {activating ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Activating...
                </>
              ) : (
                <>
                  <Power className="h-4 w-4 mr-2" />
                  Activate
                </>
              )}
            </Button>
            <Button
              onClick={handleDeactivate}
              disabled={deactivating || !status?.flags.active}
              variant="destructive"
            >
              {deactivating ? (
                <>
                  <Loader className="h-4 w-4 mr-2 animate-spin" />
                  Deactivating...
                </>
              ) : (
                <>
                  <PowerOff className="h-4 w-4 mr-2" />
                  Deactivate (Kill-Switch)
                </>
              )}
            </Button>
          </div>
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Activation Requirements</AlertTitle>
            <AlertDescription>
              Activation is only possible if all 6 gates pass. Deactivation is always available as a kill-switch.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Recent Events */}
      {status && status.recent_events.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Activation Events</CardTitle>
            <CardDescription>Audit trail of activation decisions</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Reason</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {status.recent_events.map((event, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <Badge variant="outline">{event.event_type}</Badge>
                    </TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(event.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {event.reason || "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Evaluation Modal */}
      {showEvaluationModal && evaluationResult && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle>Activation Gate Evaluation Results</CardTitle>
                  <CardDescription>
                    {evaluationResult.eligible ? (
                      <span className="text-green-600 font-semibold">All gates passed - Eligible for activation</span>
                    ) : (
                      <span className="text-red-600 font-semibold">Some gates failed - Not eligible</span>
                    )}
                  </CardDescription>
                </div>
                <Button variant="ghost" onClick={() => setShowEvaluationModal(false)}>
                  Close
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-semibold mb-2">Recommended Settings</p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Scope</p>
                    <p className="text-sm font-medium">{evaluationResult.decision.recommended_scope}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Model</p>
                    <p className="text-sm font-medium">{evaluationResult.decision.recommended_model}</p>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-sm font-semibold mb-2">Gate Results</p>
                <div className="space-y-2">
                  {evaluationResult.gates.map((gate, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded border ${
                        gate.passed ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {gate.passed ? (
                          <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                        )}
                        <div className="flex-1">
                          <p className="font-semibold text-sm">{gate.name}</p>
                          <p className="text-xs text-muted-foreground mt-1">{gate.notes}</p>
                        </div>
                        <Badge variant={gate.passed ? "default" : "destructive"}>
                          {gate.passed ? "PASS" : "FAIL"}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button
                  onClick={handleActivate}
                  disabled={!evaluationResult.eligible || activating}
                  variant="default"
                  className="flex-1"
                >
                  {activating ? (
                    <>
                      <Loader className="h-4 w-4 mr-2 animate-spin" />
                      Activating...
                    </>
                  ) : (
                    <>
                      <Power className="h-4 w-4 mr-2" />
                      Activate IRT
                    </>
                  )}
                </Button>
                <Button onClick={() => setShowEvaluationModal(false)} variant="outline">
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
