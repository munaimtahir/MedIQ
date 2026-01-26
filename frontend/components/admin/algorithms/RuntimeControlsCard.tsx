"use client";

import { useState, useMemo, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ConfirmationModal } from "./ConfirmationModal";
import { stageRuntimeSwitch } from "@/lib/admin/stageActions";
import { notify } from "@/lib/notify";
import type {
  AlgoRuntimeProfile,
  AlgoModule,
  AlgoVersion,
  RuntimePayload,
} from "@/lib/admin/algorithms/api";

interface RuntimeControlsCardProps {
  data: RuntimePayload | null;
  loading: boolean;
  onSwitch: (
    profile: AlgoRuntimeProfile,
    overrides: Partial<Record<AlgoModule, AlgoVersion>>,
    reason: string,
    confirmationPhrase?: string,
    coApproverCode?: string,
  ) => Promise<void>;
}

const MODULES: Array<{ key: AlgoModule; label: string }> = [
  { key: "mastery", label: "Mastery" },
  { key: "revision", label: "Revision" },
  { key: "difficulty", label: "Difficulty" },
  { key: "adaptive", label: "Adaptive" },
  { key: "mistakes", label: "Mistakes" },
];

// Shadow modules (not in MODULES list, handled separately in Learning Ops)
// - irt: shadow/v1
// - rank: shadow/v1
// - graph_revision: shadow/v1

export function RuntimeControlsCard({ data, loading, onSwitch }: RuntimeControlsCardProps) {
  const [selectedProfile, setSelectedProfile] = useState<AlgoRuntimeProfile>("V1_PRIMARY");
  const [overrides, setOverrides] = useState<Partial<Record<AlgoModule, AlgoVersion>>>({});
  const [reason, setReason] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize from data
  useEffect(() => {
    if (data) {
      setSelectedProfile(data.config.active_profile);
      setOverrides(data.config.overrides || {});
    }
  }, [data]);

  // Compute effective versions
  const effectiveVersions = useMemo(() => {
    const result: Record<AlgoModule, AlgoVersion> = {} as Record<AlgoModule, AlgoVersion>;
    MODULES.forEach((module) => {
      const override = overrides[module.key];
      if (override && override !== "inherit") {
        result[module.key] = override;
      } else {
        result[module.key] = selectedProfile === "V1_PRIMARY" ? "v1" : "v0";
      }
    });
    return result;
  }, [selectedProfile, overrides]);

  // Check if there are changes
  const hasChanges = useMemo(() => {
    if (!data) return false;
    if (selectedProfile !== data.config.active_profile) return true;
    const currentOverrides = data.config.overrides || {};
    return JSON.stringify(overrides) !== JSON.stringify(currentOverrides);
  }, [data, selectedProfile, overrides]);

  const canApply = reason.trim().length >= 10 && hasChanges && !isSubmitting;

  const handlePreview = () => {
    setShowPreview(true);
  };

  const handleApply = async (confirmationPhrase: string, coApproverCode?: string) => {
    setIsSubmitting(true);
    try {
      // Filter out "inherit" overrides
      const cleanOverrides: Partial<Record<AlgoModule, AlgoVersion>> = {};
      Object.entries(overrides).forEach(([key, value]) => {
        if (value && value !== "inherit") {
          cleanOverrides[key as AlgoModule] = value;
        }
      });

      await onSwitch(selectedProfile, cleanOverrides, reason, confirmationPhrase, coApproverCode);
      setShowPreview(false);
      setReason("");
    } catch (error) {
      // Error handled by hook
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setOverrides({});
  };

  const handleStage = () => {
    if (!data) {
      notify.error("No data", "Cannot stage changes without current runtime data");
      return;
    }
    stageRuntimeSwitch(
      selectedProfile,
      overrides,
      data.config.active_profile,
      data.config.overrides || {},
    );
    notify.success("Changes staged", "Review and apply from the Change Review drawer");
  };

  const newConfig = {
    active_profile: selectedProfile,
    overrides: Object.fromEntries(
      Object.entries(overrides).filter(([_, v]) => v && v !== "inherit")
    ),
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Runtime Controls</CardTitle>
          <CardDescription>
            Switch algorithm profile and set per-module overrides
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Global Profile */}
          <div className="space-y-2">
            <Label>Global Profile</Label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="profile"
                  value="V1_PRIMARY"
                  checked={selectedProfile === "V1_PRIMARY"}
                  onChange={(e) => setSelectedProfile(e.target.value as AlgoRuntimeProfile)}
                  className="h-4 w-4"
                />
                <span>V1_PRIMARY</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="profile"
                  value="V0_FALLBACK"
                  checked={selectedProfile === "V0_FALLBACK"}
                  onChange={(e) => setSelectedProfile(e.target.value as AlgoRuntimeProfile)}
                  className="h-4 w-4"
                />
                <span>V0_FALLBACK</span>
              </label>
            </div>
          </div>

          {/* Per-Module Overrides */}
          <div className="space-y-2">
            <Label>Per-Module Overrides</Label>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Module</TableHead>
                  <TableHead>Effective</TableHead>
                  <TableHead>Override</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {MODULES.map((module) => (
                  <TableRow key={module.key}>
                    <TableCell className="font-medium">{module.label}</TableCell>
                    <TableCell>
                      <Badge variant={effectiveVersions[module.key] === "v1" ? "default" : "secondary"}>
                        {effectiveVersions[module.key]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={overrides[module.key] || "inherit"}
                        onValueChange={(value) => {
                          if (value === "inherit") {
                            setOverrides((prev) => {
                              const next = { ...prev };
                              delete next[module.key];
                              return next;
                            });
                          } else {
                            setOverrides((prev) => ({
                              ...prev,
                              [module.key]: value as AlgoVersion,
                            }));
                          }
                        }}
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="inherit">Inherit</SelectItem>
                          <SelectItem value="v0">v0</SelectItem>
                          <SelectItem value="v1">v1</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Reason */}
          <div className="space-y-2">
            <Label htmlFor="reason">
              Reason <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="reason"
              placeholder="Explain why you are making this change (minimum 10 characters)..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              className={reason.length > 0 && reason.length < 10 ? "border-destructive" : ""}
            />
            {reason.length > 0 && reason.length < 10 && (
              <p className="text-sm text-destructive">
                Reason must be at least 10 characters
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button
              onClick={handleStage}
              variant="default"
              disabled={!hasChanges}
              className="flex-1"
            >
              Stage changes
            </Button>
            <Button onClick={handlePreview} variant="outline" disabled={!hasChanges}>
              Preview Changes
            </Button>
            <Button
              onClick={handlePreview}
              disabled={!canApply}
              className={isSubmitting ? "opacity-50" : ""}
            >
              {isSubmitting ? "Applying..." : "Apply Now"}
            </Button>
            <Button onClick={handleReset} variant="outline" disabled={Object.keys(overrides).length === 0}>
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preview/Confirmation Dialog */}
      <ConfirmationModal
        open={showPreview}
        onOpenChange={setShowPreview}
        actionType={
          selectedProfile !== data?.config.active_profile
            ? "PROFILE_SWITCH"
            : Object.keys(newConfig.overrides || {}).length > 0
              ? "OVERRIDES_APPLY"
              : "OVERRIDES_APPLY"
        }
        targetProfile={selectedProfile}
        previousConfig={{
          active_profile: data?.config.active_profile || "V1_PRIMARY",
          overrides: data?.config.overrides || {},
        }}
        newConfig={newConfig}
        onConfirm={handleApply}
        isSubmitting={isSubmitting}
        impactMetrics={undefined} // TODO: Add impact metrics from runtime payload
      />
    </>
  );
}
