"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Calendar, ChevronDown, Clock, PlayCircle, CheckCircle2, AlertCircle } from "lucide-react";
import { notify } from "@/lib/notify";
import {
  getRevisionQueue,
  updateRevisionQueueItem,
  type RevisionQueueItem,
} from "@/lib/api/revisionApi";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { format, isToday } from "date-fns";

type TabValue = "today" | "upcoming";

function getPriorityLabel(score: number): {
  label: string;
  variant: "destructive" | "default" | "secondary";
} {
  if (score >= 70) return { label: "High", variant: "destructive" };
  if (score >= 40) return { label: "Medium", variant: "default" };
  return { label: "Low", variant: "secondary" };
}

function formatReasonText(reason: RevisionQueueItem["reason"]): string {
  const parts: string[] = [];

  if (reason.mastery_band) {
    const bandText = reason.mastery_band.charAt(0).toUpperCase() + reason.mastery_band.slice(1);
    const scoreText =
      reason.mastery_score !== undefined ? ` (${(reason.mastery_score * 100).toFixed(0)}%)` : "";
    parts.push(`${bandText} mastery${scoreText}`);
  }

  if (reason.days_since_last !== undefined) {
    const days = Math.floor(reason.days_since_last);
    parts.push(`${days} day${days !== 1 ? "s" : ""} since last attempt`);
  }

  return parts.length > 0 ? parts.join(", ") : "Scheduled for revision";
}

interface RevisionCardProps {
  item: RevisionQueueItem;
  onStart: (item: RevisionQueueItem) => void;
  onDone: (itemId: string) => void;
  onSnooze: (itemId: string, days: number) => void;
  isProcessing: boolean;
}

function RevisionCard({ item, onStart, onDone, onSnooze, isProcessing }: RevisionCardProps) {
  const priority = getPriorityLabel(item.priority_score);
  const dueDate = new Date(item.due_date);
  const isDueToday = isToday(dueDate);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex items-center gap-2">
              <Badge variant={priority.variant}>{priority.label} Priority</Badge>
              <Badge variant="outline">{item.block.name}</Badge>
            </div>
            <CardTitle className="mb-1 text-xl">{item.theme.name}</CardTitle>
            <CardDescription className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4" />
              Due {isDueToday ? "Today" : format(dueDate, "MMM d, yyyy")}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Why Section */}
          <div className="rounded-lg bg-muted p-3">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium">Why? </span>
              {formatReasonText(item.reason)}
            </p>
          </div>

          {/* Recommended Count */}
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              Recommended:{" "}
              <span className="font-medium text-foreground">
                {item.recommended_count} questions
              </span>
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2">
            <Button onClick={() => onStart(item)} disabled={isProcessing} className="flex-1">
              <PlayCircle className="mr-2 h-4 w-4" />
              Start Practice
            </Button>

            <Button
              onClick={() => onDone(item.id)}
              disabled={isProcessing}
              variant="outline"
              size="icon"
            >
              <CheckCircle2 className="h-4 w-4" />
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button disabled={isProcessing} variant="outline" size="icon">
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onSnooze(item.id, 1)}>
                  Snooze 1 day
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onSnooze(item.id, 2)}>
                  Snooze 2 days
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onSnooze(item.id, 3)}>
                  Snooze 3 days
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function RevisionPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabValue>("today");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<RevisionQueueItem[]>([]);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    loadQueue();
  }, [activeTab]);

  async function loadQueue() {
    setLoading(true);
    setError(null);

    try {
      const scope = activeTab === "today" ? "today" : "week";
      const data = await getRevisionQueue(scope, "DUE");
      setItems(data.items);
    } catch (err: unknown) {
      console.error("Failed to load revision queue:", err);
      setError(err?.message || "Failed to load revision queue");
    } finally {
      setLoading(false);
    }
  }

  async function handleStart(item: RevisionQueueItem) {
    // Navigate to practice builder with theme pre-selected
    const params = new URLSearchParams({
      themeId: item.theme.id,
      count: item.recommended_count.toString(),
    });
    router.push(`/student/practice/build?${params}`);
  }

  async function handleDone(itemId: string) {
    setProcessingId(itemId);

    try {
      await updateRevisionQueueItem(itemId, { action: "DONE" });
      setItems((prev) => prev.filter((item) => item.id !== itemId));
      notify.success("Marked as done", "This revision item has been completed");
    } catch (err: unknown) {
      console.error("Failed to update item:", err);
      notify.error("Failed to update", err?.message || "Please try again");
    } finally {
      setProcessingId(null);
    }
  }

  async function handleSnooze(itemId: string, days: number) {
    setProcessingId(itemId);

    try {
      await updateRevisionQueueItem(itemId, { action: "SNOOZE", snooze_days: days });
      setItems((prev) => prev.filter((item) => item.id !== itemId));
      notify.success(
        "Snoozed",
        `This revision will reappear in ${days} day${days !== 1 ? "s" : ""}`,
      );
    } catch (err: unknown) {
      console.error("Failed to snooze item:", err);
      notify.error("Failed to snooze", err?.message || "Please try again");
    } finally {
      setProcessingId(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="mb-2 h-10 w-64" />
          <Skeleton className="h-5 w-96" />
        </div>
        <Skeleton className="h-12 w-full" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">Revision Queue</h1>
          <p className="text-muted-foreground">Scheduled revision based on your mastery</p>
        </div>
        <Card>
          <CardContent className="py-6">
            <InlineAlert variant="error" message={error} />
            <Button onClick={loadQueue} className="mt-4">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="flex items-center gap-2 text-3xl font-bold">
          <Calendar className="h-8 w-8" />
          Revision Queue
        </h1>
        <p className="text-muted-foreground">Scheduled revision based on your mastery</p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
        <TabsList>
          <TabsTrigger value="today">Today</TabsTrigger>
          <TabsTrigger value="upcoming">Upcoming (7 days)</TabsTrigger>
        </TabsList>

        <TabsContent value="today" className="mt-6">
          {items.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-muted-foreground">
                  <CheckCircle2 className="mx-auto mb-4 h-16 w-16 opacity-30" />
                  <p className="mb-2 text-lg font-medium">All clear for today!</p>
                  <p className="text-sm">
                    No revisions due today. Check back tomorrow or view upcoming items.
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {items.length} revision{items.length !== 1 ? "s" : ""} due today
                </p>
              </div>
              {items.map((item) => (
                <RevisionCard
                  key={item.id}
                  item={item}
                  onStart={handleStart}
                  onDone={handleDone}
                  onSnooze={handleSnooze}
                  isProcessing={processingId === item.id}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="upcoming" className="mt-6">
          {items.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-muted-foreground">
                  <AlertCircle className="mx-auto mb-4 h-16 w-16 opacity-30" />
                  <p className="mb-2 text-lg font-medium">No upcoming revisions</p>
                  <p className="text-sm">
                    Complete more practice sessions to build your revision schedule.
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {items.length} revision{items.length !== 1 ? "s" : ""} in the next 7 days
                </p>
              </div>
              {items.map((item) => (
                <RevisionCard
                  key={item.id}
                  item={item}
                  onStart={handleStart}
                  onDone={handleDone}
                  onSnooze={handleSnooze}
                  isProcessing={processingId === item.id}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
