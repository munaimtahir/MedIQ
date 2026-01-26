"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Upload } from "lucide-react";
import { CsvImportDialog } from "@/components/admin/syllabus/CsvImportDialog";
import { TemplatesMenu } from "@/components/admin/syllabus/TemplatesMenu";

// Lazy load heavy syllabus manager component
const SyllabusManager = dynamic(
  () => import("@/components/admin/syllabus/SyllabusManager").then((mod) => ({ 
    default: mod.SyllabusManager 
  })),
  { 
    loading: () => <Skeleton className="h-[600px] w-full rounded-lg" />,
    ssr: false,
  }
);

export default function SyllabusPage() {
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Syllabus Management</h1>
          <p className="text-muted-foreground">Manage years, blocks, and themes</p>
        </div>
        <div className="flex gap-2">
          <TemplatesMenu />
          <Button onClick={() => setImportDialogOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Import (CSV)
          </Button>
        </div>
      </div>

      {/* Main Manager */}
      <SyllabusManager />

      {/* CSV Import Dialog */}
      <CsvImportDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onSuccess={() => {
          // Refetch data will be handled by individual hooks
          setImportDialogOpen(false);
        }}
      />
    </div>
  );
}
