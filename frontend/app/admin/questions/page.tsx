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
import { adminAPI } from "@/lib/api";
import { Question } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function QuestionsPage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<Question[]>([]);
  const [filter, setFilter] = useState<"all" | "published" | "unpublished">("all");
  const [loading, setLoading] = useState(true);

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const published = filter === "all" ? undefined : filter === "published";
      const qs = await adminAPI.listQuestions(0, 100, published);
      setQuestions(qs);
    } catch (error) {
      console.error("Failed to load questions:", error);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const handlePublish = async (id: number) => {
    try {
      await adminAPI.publishQuestion(id);
      loadQuestions();
    } catch (error) {
      console.error("Failed to publish:", error);
      alert("Failed to publish question");
    }
  };

  const handleUnpublish = async (id: number) => {
    try {
      await adminAPI.unpublishQuestion(id);
      loadQuestions();
    } catch (error) {
      console.error("Failed to unpublish:", error);
      alert("Failed to unpublish question");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Questions</h1>
          <p className="text-muted-foreground">Manage all questions</p>
        </div>
        <div className="flex gap-4">
          <Select value={filter} onValueChange={(v) => setFilter(v as any)}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="published">Published</SelectItem>
              <SelectItem value="unpublished">Unpublished</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => router.push("/admin/questions/new")}>Create New Question</Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Question List</CardTitle>
          <CardDescription>{questions.length} questions found</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p>Loading questions...</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Question</TableHead>
                  <TableHead>Difficulty</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {questions.map((q) => (
                  <TableRow key={q.id}>
                    <TableCell className="font-medium">{q.id}</TableCell>
                    <TableCell className="max-w-md truncate">{q.question_text}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{q.difficulty || "N/A"}</Badge>
                    </TableCell>
                    <TableCell>
                      {q.is_published ? (
                        <Badge variant="success">Published</Badge>
                      ) : (
                        <Badge variant="secondary">Draft</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/admin/questions/${q.id}`)}
                        >
                          Edit
                        </Button>
                        {q.is_published ? (
                          <Button variant="outline" size="sm" onClick={() => handleUnpublish(q.id)}>
                            Unpublish
                          </Button>
                        ) : (
                          <Button variant="default" size="sm" onClick={() => handlePublish(q.id)}>
                            Publish
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
    </div>
  );
}
