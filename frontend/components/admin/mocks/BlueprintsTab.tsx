"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Edit, Play, Archive, FileText } from "lucide-react";
import { adminMocksAPI, type MockBlueprint } from "@/lib/api/adminMocks";
import { notify } from "@/lib/notify";
import { BlueprintEditor } from "./BlueprintEditor";
import { GenerateMockModal } from "./GenerateMockModal";
import { PoliceConfirmModal } from "@/components/admin/learningOps/PoliceConfirmModal";
import { formatDistanceToNow } from "date-fns";
import { useUserStore } from "@/store/userStore";

export function BlueprintsTab() {
  const [blueprints, setBlueprints] = useState<MockBlueprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [yearFilter, setYearFilter] = useState<number | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<"DRAFT" | "ACTIVE" | "ARCHIVED" | undefined>(undefined);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingBlueprint, setEditingBlueprint] = useState<MockBlueprint | null>(null);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [generatingBlueprint, setGeneratingBlueprint] = useState<MockBlueprint | null>(null);
  const [activateModalOpen, setActivateModalOpen] = useState(false);
  const [activatingBlueprint, setActivatingBlueprint] = useState<MockBlueprint | null>(null);
  const [archiveModalOpen, setArchiveModalOpen] = useState(false);
  const [archivingBlueprint, setArchivingBlueprint] = useState<MockBlueprint | null>(null);
  const [activateReason, setActivateReason] = useState("");
  const [archiveReason, setArchiveReason] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const userRole = useUserStore((state) => state.user?.role);
  const isAdmin = userRole === "ADMIN";

  const fetchBlueprints = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminMocksAPI.listBlueprints({
        year: yearFilter,
        status: statusFilter,
      });
      setBlueprints(data);
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to load blueprints", err.message);
    } finally {
      setLoading(false);
    }
  }, [yearFilter, statusFilter]);

  useEffect(() => {
    fetchBlueprints();
  }, [fetchBlueprints]);

  const handleCreateBlueprint = () => {
    setEditingBlueprint(null);
    setEditorOpen(true);
  };

  const handleEditBlueprint = (blueprint: MockBlueprint) => {
    setEditingBlueprint(blueprint);
    setEditorOpen(true);
  };

  const handleSaveBlueprint = async () => {
    await fetchBlueprints();
    setEditorOpen(false);
    setEditingBlueprint(null);
  };

  const handleActivate = (blueprint: MockBlueprint) => {
    setActivatingBlueprint(blueprint);
    setActivateReason("");
    setActivateModalOpen(true);
  };

  const handleArchive = (blueprint: MockBlueprint) => {
    setArchivingBlueprint(blueprint);
    setArchiveReason("");
    setArchiveModalOpen(true);
  };

  const handleGenerate = (blueprint: MockBlueprint) => {
    setGeneratingBlueprint(blueprint);
    setGenerateModalOpen(true);
  };

  const handleConfirmActivate = async () => {
    if (!activatingBlueprint) return;
    setIsSubmitting(true);
    try {
      await adminMocksAPI.activateBlueprint(activatingBlueprint.id, {
        reason: activateReason,
        confirmation_phrase: "ACTIVATE MOCK BLUEPRINT",
      });
      notify.success("Blueprint activated", `"${activatingBlueprint.title}" is now active`);
      await fetchBlueprints();
      setActivateModalOpen(false);
      setActivatingBlueprint(null);
      setActivateReason("");
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to activate blueprint", err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmArchive = async () => {
    if (!archivingBlueprint) return;
    setIsSubmitting(true);
    try {
      await adminMocksAPI.archiveBlueprint(archivingBlueprint.id, {
        reason: archiveReason,
        confirmation_phrase: "ARCHIVE MOCK BLUEPRINT",
      });
      notify.success("Blueprint archived", `"${archivingBlueprint.title}" has been archived`);
      await fetchBlueprints();
      setArchiveModalOpen(false);
      setArchivingBlueprint(null);
      setArchiveReason("");
    } catch (error) {
      const err = error as Error;
      notify.error("Failed to archive blueprint", err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="text-muted-foreground">Loading blueprints...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Filters and Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Select
            value={yearFilter?.toString() || "all"}
            onValueChange={(value) => setYearFilter(value === "all" ? undefined : parseInt(value))}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Years" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Years</SelectItem>
              <SelectItem value="1">Year 1</SelectItem>
              <SelectItem value="2">Year 2</SelectItem>
              <SelectItem value="3">Year 3</SelectItem>
              <SelectItem value="4">Year 4</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={statusFilter || "all"}
            onValueChange={(value) =>
              setStatusFilter(value === "all" ? undefined : (value as "DRAFT" | "ACTIVE" | "ARCHIVED"))
            }
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="DRAFT">Draft</SelectItem>
              <SelectItem value="ACTIVE">Active</SelectItem>
              <SelectItem value="ARCHIVED">Archived</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button onClick={handleCreateBlueprint}>
          <Plus className="mr-2 h-4 w-4" />
          Create Blueprint
        </Button>
      </div>

      {/* Table */}
      {blueprints.length === 0 ? (
        <div className="rounded-lg border p-8 text-center text-muted-foreground">
          No blueprints found. Create your first blueprint to get started.
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Year</TableHead>
                <TableHead>Questions</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {blueprints.map((blueprint) => (
                <TableRow key={blueprint.id}>
                  <TableCell className="font-medium">{blueprint.title}</TableCell>
                  <TableCell>Year {blueprint.year}</TableCell>
                  <TableCell>{blueprint.total_questions}</TableCell>
                  <TableCell>{blueprint.duration_minutes} min</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        blueprint.status === "ACTIVE"
                          ? "default"
                          : blueprint.status === "ARCHIVED"
                            ? "secondary"
                            : "outline"
                      }
                    >
                      {blueprint.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDistanceToNow(new Date(blueprint.updated_at), { addSuffix: true })}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditBlueprint(blueprint)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      {isAdmin && blueprint.status !== "ACTIVE" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleActivate(blueprint)}
                          disabled={blueprint.status === "ARCHIVED"}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                      {isAdmin && blueprint.status === "ACTIVE" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleGenerate(blueprint)}
                        >
                          <FileText className="h-4 w-4" />
                        </Button>
                      )}
                      {isAdmin && blueprint.status !== "ARCHIVED" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleArchive(blueprint)}
                        >
                          <Archive className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Editor */}
      {editorOpen && (
        <BlueprintEditor
          open={editorOpen}
          onOpenChange={setEditorOpen}
          blueprint={editingBlueprint}
          onSave={handleSaveBlueprint}
        />
      )}

      {/* Generate Modal */}
      {generateModalOpen && generatingBlueprint && (
        <GenerateMockModal
          open={generateModalOpen}
          onOpenChange={setGenerateModalOpen}
          blueprint={generatingBlueprint}
          onSuccess={() => {
            setGenerateModalOpen(false);
            setGeneratingBlueprint(null);
            fetchBlueprints();
          }}
        />
      )}

      {/* Activate Modal */}
      {activateModalOpen && activatingBlueprint && (
        <PoliceConfirmModal
          open={activateModalOpen}
          onOpenChange={setActivateModalOpen}
          actionTitle={`Activate Blueprint "${activatingBlueprint.title}"`}
          requiredPhrase="ACTIVATE MOCK BLUEPRINT"
          reason={activateReason}
          onReasonChange={setActivateReason}
          onConfirm={handleConfirmActivate}
          isSubmitting={isSubmitting}
          variant="default"
        />
      )}

      {/* Archive Modal */}
      {archiveModalOpen && archivingBlueprint && (
        <PoliceConfirmModal
          open={archiveModalOpen}
          onOpenChange={setArchiveModalOpen}
          actionTitle={`Archive Blueprint "${archivingBlueprint.title}"`}
          requiredPhrase="ARCHIVE MOCK BLUEPRINT"
          reason={archiveReason}
          onReasonChange={setArchiveReason}
          onConfirm={handleConfirmArchive}
          isSubmitting={isSubmitting}
          variant="destructive"
        />
      )}
    </div>
  );
}
