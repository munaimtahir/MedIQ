"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Download } from "lucide-react";
import { notify } from "@/lib/notify";

export function TemplatesMenu() {
  const handleDownload = async (type: "years" | "blocks" | "themes") => {
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
      notify.success("Template downloaded", `Downloaded ${type} template`);
    } catch (error) {
      notify.error("Download failed", error instanceof Error ? error.message : "Failed to download template");
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Download Templates
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => handleDownload("years")}>
          Years Template
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleDownload("blocks")}>
          Blocks Template
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleDownload("themes")}>
          Themes Template
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
