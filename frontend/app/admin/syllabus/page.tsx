"use client";

import { useEffect, useState } from "react";
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
import { Block, Theme } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function SyllabusPage() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [selectedYear, setSelectedYear] = useState<number>(1);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([syllabusAPI.getBlocks(selectedYear), syllabusAPI.getThemes()])
      .then(([blks, thms]) => {
        setBlocks(blks);
        setThemes(thms);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedYear]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Syllabus Management</h1>
          <p className="text-muted-foreground">Manage blocks and themes</p>
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

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Blocks</CardTitle>
            <CardDescription>Year {selectedYear} blocks</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p>Loading...</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {blocks.map((block) => (
                    <TableRow key={block.id}>
                      <TableCell className="font-medium">{block.id}</TableCell>
                      <TableCell>{block.name}</TableCell>
                      <TableCell className="text-muted-foreground">{block.description}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Themes</CardTitle>
            <CardDescription>All themes</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p>Loading...</p>
            ) : (
              <div className="max-h-96 space-y-2 overflow-y-auto">
                {themes.map((theme) => (
                  <div key={theme.id} className="rounded border p-2">
                    <p className="font-medium">{theme.name}</p>
                    <p className="text-sm text-muted-foreground">Block {theme.block_id}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
