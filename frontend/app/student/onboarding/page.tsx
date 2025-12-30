"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { syllabusAPI } from "@/lib/api";
import { Block } from "@/lib/api";
import { useEffect } from "react";

export default function OnboardingPage() {
  const router = useRouter();
  const [selectedYear, setSelectedYear] = useState<number>(1);
  const [selectedBlock, setSelectedBlock] = useState<string>("");
  const [blocks, setBlocks] = useState<Block[]>([]);

  useEffect(() => {
    syllabusAPI.getBlocks(selectedYear).then(setBlocks);
  }, [selectedYear]);

  const handleComplete = () => {
    // In a real app, save preferences
    router.push("/student/dashboard");
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Welcome! Let&apos;s get started</CardTitle>
          <CardDescription>Select your year and primary block</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Year</label>
            <Select
              value={selectedYear.toString()}
              onValueChange={(v) => setSelectedYear(Number(v))}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Year 1</SelectItem>
                <SelectItem value="2">Year 2</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Primary Block</label>
            <Select value={selectedBlock} onValueChange={setSelectedBlock}>
              <SelectTrigger>
                <SelectValue placeholder="Select a block" />
              </SelectTrigger>
              <SelectContent>
                {blocks.map((block) => (
                  <SelectItem key={block.id} value={block.id}>
                    {block.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button onClick={handleComplete} className="w-full" disabled={!selectedBlock}>
            Complete Setup
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
