"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface CsvToolsCardProps {
  loading?: boolean;
}

export function CsvToolsCard({ loading }: CsvToolsCardProps) {
  const router = useRouter();

  const handleDownloadTemplate = async (type: "years" | "blocks" | "themes") => {
    try {
      const response = await fetch(`/api/admin/syllabus/import/templates/${type}`, {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to download template");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${type}_template.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error(`Failed to download ${type} template:`, error);
      // Fallback: navigate to syllabus manager
      router.push("/admin/syllabus");
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-64 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>CSV Tools</CardTitle>
        <CardDescription>Import and export syllabus data</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <p className="text-sm font-medium">Download Templates</p>
          <div className="flex flex-col gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDownloadTemplate("years")}
              className="w-full justify-start"
            >
              <Download className="mr-2 h-4 w-4" />
              Years Template
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDownloadTemplate("blocks")}
              className="w-full justify-start"
            >
              <Download className="mr-2 h-4 w-4" />
              Blocks Template
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleDownloadTemplate("themes")}
              className="w-full justify-start"
            >
              <Download className="mr-2 h-4 w-4" />
              Themes Template
            </Button>
          </div>
        </div>

        <div className="pt-2 border-t">
          <Button
            variant="default"
            onClick={() => router.push("/admin/syllabus#import")}
            className="w-full"
          >
            <Upload className="mr-2 h-4 w-4" />
            Open Syllabus Import
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
