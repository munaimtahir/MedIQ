"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { adminImportApi } from "@/lib/admin/importApi";
import type { ImportSchemaListItem } from "@/lib/types/import";
import { SkeletonTable } from "@/components/status/SkeletonTable";
import { EmptyState } from "@/components/status/EmptyState";
import { ErrorState } from "@/components/status/ErrorState";
import { notify } from "@/lib/notify";
import { FileText, Download, CheckCircle, Plus } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function ImportSchemasPage() {
  const router = useRouter();
  const [schemas, setSchemas] = useState<ImportSchemaListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadSchemas = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminImportApi.listSchemas();
      setSchemas(data);
    } catch (err) {
      console.error("Failed to load schemas:", err);
      setError(err instanceof Error ? err : new Error("Failed to load schemas"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchemas();
  }, [loadSchemas]);

  const handleActivate = async (id: string, name: string) => {
    try {
      await adminImportApi.activateSchema(id);
      notify.success("Schema Activated", `Schema "${name}" is now active`);
      loadSchemas();
    } catch (error) {
      notify.error(
        "Activation Failed",
        error instanceof Error ? error.message : "Failed to activate schema",
      );
    }
  };

  const handleDownloadTemplate = async (id: string, name: string, version: number) => {
    try {
      const blob = await adminImportApi.downloadTemplate(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name}_v${version}_template.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      notify.success("Template Downloaded", `Template for ${name} v${version} downloaded`);
    } catch (error) {
      notify.error(
        "Download Failed",
        error instanceof Error ? error.message : "Failed to download template",
      );
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Import Schemas</h1>
          <p className="text-muted-foreground">Manage CSV/JSON import configurations</p>
        </div>
        <Button onClick={() => router.push("/admin/import/schemas/new")}>
          <Plus className="mr-2 h-4 w-4" />
          Create Schema
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Import Schemas</CardTitle>
          <CardDescription>
            {!loading && !error && `${schemas.length} schemas configured`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <SkeletonTable rows={5} cols={6} />
          ) : error ? (
            <ErrorState
              variant="card"
              title="Failed to load schemas"
              description={error.message}
              actionLabel="Retry"
              onAction={loadSchemas}
            />
          ) : schemas.length === 0 ? (
            <EmptyState
              variant="card"
              title="No schemas configured"
              description="Get started by creating your first import schema."
              icon={<FileText className="h-8 w-8 text-slate-400" />}
              actionLabel="Create Schema"
              onAction={() => router.push("/admin/import/schemas/new")}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead className="w-[100px]">Version</TableHead>
                  <TableHead className="w-[100px]">Status</TableHead>
                  <TableHead className="w-[100px]">Type</TableHead>
                  <TableHead className="w-[150px]">Updated</TableHead>
                  <TableHead className="w-[250px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schemas.map((schema) => (
                  <TableRow key={schema.id}>
                    <TableCell className="font-medium">{schema.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">v{schema.version}</Badge>
                    </TableCell>
                    <TableCell>
                      {schema.is_active ? (
                        <Badge className="bg-green-500">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Active
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{schema.file_type.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(schema.updated_at || schema.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/admin/import/schemas/${schema.id}`)}
                        >
                          View
                        </Button>
                        {!schema.is_active && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleActivate(schema.id, schema.name)}
                          >
                            Activate
                          </Button>
                        )}
                        {schema.file_type === "csv" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              handleDownloadTemplate(schema.id, schema.name, schema.version)
                            }
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">About Import Schemas</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            Import schemas define how CSV/JSON files are parsed and mapped to question fields. Each
            schema can have multiple versions to accommodate changes over time.
          </p>
          <p className="font-medium">Key features:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Only one schema can be active at a time (used for imports without schema_id)</li>
            <li>Versioning prevents breaking old import jobs</li>
            <li>Download template CSV to see expected format</li>
            <li>Create new versions to update mapping without losing history</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
