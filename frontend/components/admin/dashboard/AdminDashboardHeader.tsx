"use client";

import { Button } from "@/components/ui/button";
import { Plus, BookOpen } from "lucide-react";
import { useRouter } from "next/navigation";

export function AdminDashboardHeader() {
  const router = useRouter();

  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground">System overview and quick actions</p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => router.push("/admin/syllabus")}>
          <BookOpen className="mr-2 h-4 w-4" />
          Syllabus Manager
        </Button>
        <Button onClick={() => router.push("/admin/questions/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Question
        </Button>
      </div>
    </div>
  );
}
