"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Upload, FileText, CheckCircle2, XCircle } from "lucide-react";
import { useCsvImport } from "@/lib/admin/syllabus/hooks";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface CsvImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function CsvImportDialog({
  open,
  onOpenChange,
  onSuccess,
}: CsvImportDialogProps) {
  const [importType, setImportType] = useState<"years" | "blocks" | "themes">("years");
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [autoCreate, setAutoCreate] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message?: string;
    rows_processed?: number;
    rows_failed?: number;
    errors?: Array<{ row: number; reason?: string; message?: string }>;
  } | null>(null);

  const { importCsv, importing } = useCsvImport();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
    }
  };

  const handleImport = async () => {
    if (!file) return;

    try {
      const importResult = await importCsv(importType, file, dryRun, autoCreate);
      setResult(importResult);
      if (!dryRun && onSuccess) {
        onSuccess();
      }
    } catch {
      // Error already handled in hook
    }
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    setDryRun(true);
    setAutoCreate(false);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Import CSV</DialogTitle>
          <DialogDescription>
            Upload a CSV file to import years, blocks, or themes
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Import Type */}
          <div className="space-y-2">
            <Label>Import Type</Label>
            <Select value={importType} onValueChange={(v) => setImportType(v as "years" | "blocks" | "themes")}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="years">Years</SelectItem>
                <SelectItem value="blocks">Blocks</SelectItem>
                <SelectItem value="themes">Themes</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label>CSV File</Label>
            <div className="flex items-center gap-2">
              <Input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="flex-1"
              />
              {file && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <FileText className="h-4 w-4" />
                  {file.name}
                </div>
              )}
            </div>
          </div>

          {/* Options */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Switch
                id="dry-run"
                checked={dryRun}
                onCheckedChange={setDryRun}
              />
              <Label htmlFor="dry-run">Dry run (validate only)</Label>
            </div>
            {(importType === "blocks" || importType === "themes") && (
              <div className="flex items-center space-x-2">
                <Switch
                  id="auto-create"
                  checked={autoCreate}
                  onCheckedChange={setAutoCreate}
                />
                <Label htmlFor="auto-create">Auto-create missing parents</Label>
              </div>
            )}
          </div>

          {/* Results */}
          {result && (
            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold">Import Results</h4>
                {result.dry_run && (
                  <Badge variant="secondary">Dry Run</Badge>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <span>Accepted: {result.accepted}</span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span>Rejected: {result.rejected}</span>
                </div>
                {!result.dry_run && (
                  <>
                    <div>Created: {result.created || 0}</div>
                    <div>Updated: {result.updated || 0}</div>
                  </>
                )}
              </div>
              {result.errors && result.errors.length > 0 && (
                <div className="mt-3">
                  <p className="text-sm font-medium mb-2">Errors:</p>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {result.errors.map((error, idx: number) => (
                      <div
                        key={idx}
                        className="text-xs p-2 bg-destructive/10 rounded border border-destructive/20"
                      >
                        <span className="font-medium">Row {error.row}:</span>{" "}
                        {error.reason || error.message}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={importing}>
            {result ? "Close" : "Cancel"}
          </Button>
          <Button
            onClick={handleImport}
            disabled={!file || importing}
          >
            <Upload className="h-4 w-4 mr-2" />
            {importing
              ? "Processing..."
              : dryRun
              ? "Validate"
              : "Import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

