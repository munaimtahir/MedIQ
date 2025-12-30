"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { syllabusAPI } from "@/lib/api";
import { Block } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function BlocksPage() {
  const router = useRouter();
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    syllabusAPI
      .getBlocks(selectedYear)
      .then(setBlocks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedYear]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Blocks</h1>
          <p className="text-muted-foreground">Select a block to view themes and questions</p>
        </div>
        <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(Number(v))}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">Year 1</SelectItem>
            <SelectItem value="2">Year 2</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <p>Loading blocks...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {blocks.map((block) => (
            <Card key={block.id} className="transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle>
                  Block {block.id}: {block.name}
                </CardTitle>
                <CardDescription>{block.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={() => router.push(`/student/blocks/${block.id}`)}
                  className="w-full"
                >
                  View Themes
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
