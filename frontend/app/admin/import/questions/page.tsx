"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { adminImportApi } from "@/lib/admin/importApi";
import type { ImportSchemaListItem } from "@/lib/types/import";
import { notify } from "@/lib/notify";
import { Upload, FileText, AlertCircle, CheckCircle, Info } from "lucide-react";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export default function ImportQuestionsPage() {
  const router = useRouter();
  const [schemas, setSchemas] = useState<ImportSchemaListItem[]>([]);
  const [selectedSchemaId, setSelectedSchemaId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSchemas = useCallback(async () => {
    try {
      const data = await adminImportApi.listSchemas();
      setSchemas(data);

      // Pre-select active schema
      const activeSchema = data.find((s) => s.is_active);
      if (activeSchema) {
        setSelectedSchemaId(activeSchema.id);
      }
    } catch (err) {
      console.error("Failed to load schemas:", err);
    }
  }, []);

  useEffect(() => {
    loadSchemas();
  }, [loadSchemas]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) {
      setFile(null);
      setError(null);
      return;
    }

    // Validate file size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError(`File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB`);
      setFile(null);
      return;
    }

    // Validate file type
    if (!selectedFile.name.endsWith(".csv")) {
      setError("Only CSV files are supported");
      setFile(null);
      return;
    }

    setFile(selectedFile);
    setError(null);
  };

  const handleImport = async () => {
    if (!file) {
      setError("Please select a file");
      return;
    }

    if (!selectedSchemaId) {
      setError("Please select a schema");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const result = await adminImportApi.importQuestions(file, {
        schemaId: selectedSchemaId,
        dryRun,
      });

      notify.success(
        dryRun ? "Dry Run Complete" : "Import Complete",
        `${result.accepted_rows} accepted, ${result.rejected_rows} rejected`,
      );

      // Navigate to job results
      router.push(`/admin/import/jobs/${result.job_id}`);
    } catch (err) {
      console.error("Import failed:", err);
      setError(err instanceof Error ? err.message : "Import failed");
      notify.error("Import Failed", err instanceof Error ? err.message : "Import failed");
    } finally {
      setUploading(false);
    }
  };

  const selectedSchema = schemas.find((s) => s.id === selectedSchemaId);

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold">Import Questions</h1>
        <p className="text-muted-foreground">Upload CSV file to bulk import questions</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload File</CardTitle>
          <CardDescription>
            Select a CSV file formatted according to your import schema
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Schema Selection */}
          <div className="space-y-2">
            <Label htmlFor="schema">Import Schema *</Label>
            <Select value={selectedSchemaId} onValueChange={setSelectedSchemaId}>
              <SelectTrigger id="schema">
                <SelectValue placeholder="Select schema" />
              </SelectTrigger>
              <SelectContent>
                {schemas.map((schema) => (
                  <SelectItem key={schema.id} value={schema.id}>
                    {schema.name} v{schema.version}
                    {schema.is_active && " (Active)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedSchema && (
              <p className="text-xs text-muted-foreground">
                Selected: {selectedSchema.name} v{selectedSchema.version}
                {selectedSchema.is_active && " • Active Schema"}
              </p>
            )}
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label htmlFor="file">CSV File *</Label>
            <div className="border-2 border-dashed rounded-lg p-8 text-center space-y-4">
              {file ? (
                <div className="space-y-2">
                  <FileText className="mx-auto h-12 w-12 text-green-500" />
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                  <Button variant="outline" size="sm" onClick={() => setFile(null)}>
                    Remove
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
                  <div>
                    <Label htmlFor="file" className="cursor-pointer text-primary hover:underline">
                      Click to upload
                    </Label>
                    <p className="text-sm text-muted-foreground">or drag and drop</p>
                  </div>
                  <p className="text-xs text-muted-foreground">CSV files only, max 10MB</p>
                  <Input
                    id="file"
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Dry Run Option */}
          <div className="flex items-center space-x-2">
            <Checkbox id="dry_run" checked={dryRun} onCheckedChange={(checked) => setDryRun(checked === true)} />
            <Label htmlFor="dry_run" className="cursor-pointer">
              Dry run (validate only, don't insert questions)
            </Label>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <div className="flex gap-4">
            <Button onClick={handleImport} disabled={!file || uploading} className="flex-1">
              {uploading ? "Importing..." : dryRun ? "Validate" : "Import Questions"}
            </Button>
            <Button variant="outline" onClick={() => router.push("/admin/import/jobs")}>
              View Jobs
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Help Card */}
      <Card className="bg-blue-50 dark:bg-blue-950">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            <CardTitle className="text-base">Import Tips</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <ul className="list-disc list-inside space-y-1">
            <li>Use <strong>Dry Run</strong> to validate your CSV before actually importing</li>
            <li>Download the template CSV from the schema page to see the expected format</li>
            <li>All questions are imported as <strong>DRAFT</strong> status</li>
            <li>Year, Block, and Theme must match existing syllabus (no auto-creation)</li>
            <li>Exactly 5 options (A-E) are required for each question</li>
            <li>Rejected rows will be available for download with error details</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
