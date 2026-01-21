"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Bookmark, Trash2, Search } from "lucide-react";
import { notify } from "@/lib/notify";
import { listBookmarks, deleteBookmark } from "@/lib/api/bookmarksApi";
import type { BookmarkWithQuestion } from "@/lib/types/bookmark";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { format } from "date-fns";

export default function BookmarksPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bookmarks, setBookmarks] = useState<BookmarkWithQuestion[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadBookmarks();
  }, []);

  async function loadBookmarks() {
    setLoading(true);
    setError(null);

    try {
      const data = await listBookmarks();
      setBookmarks(data);
    } catch (err: unknown) {
      console.error("Failed to load bookmarks:", err);
      setError(err?.message || "Failed to load bookmarks");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteBookmark(bookmarkId: string) {
    setDeletingId(bookmarkId);

    try {
      await deleteBookmark(bookmarkId);
      setBookmarks((prev) => prev.filter((b) => b.id !== bookmarkId));
      notify.success("Bookmark removed", "Question removed from bookmarks");
    } catch (err: unknown) {
      console.error("Failed to delete bookmark:", err);
      notify.error("Failed to remove bookmark", err?.message || "Please try again");
    } finally {
      setDeletingId(null);
    }
  }

  const filteredBookmarks = bookmarks.filter((bookmark) =>
    bookmark.question_stem.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <InlineAlert variant="error" message={error} />
        <Button onClick={loadBookmarks}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="flex items-center gap-2 text-3xl font-bold">
          <Bookmark className="h-8 w-8" />
          Bookmarks
        </h1>
        <p className="text-muted-foreground">Questions you&apos;ve saved for later review</p>
      </div>

      {/* Search */}
      {bookmarks.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search bookmarks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      )}

      {/* Stats */}
      {bookmarks.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Total Bookmarks</CardDescription>
              <CardTitle className="text-3xl">{bookmarks.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>With Notes</CardDescription>
              <CardTitle className="text-3xl">{bookmarks.filter((b) => b.notes).length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>Filtered Results</CardDescription>
              <CardTitle className="text-3xl">{filteredBookmarks.length}</CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* Bookmarks List */}
      {bookmarks.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-muted-foreground">
              <Bookmark className="mx-auto mb-4 h-16 w-16 opacity-30" />
              <p className="mb-2 text-lg font-medium">No bookmarks yet</p>
              <p className="text-sm">
                Click the bookmark icon on questions during review to save them here
              </p>
            </div>
          </CardContent>
        </Card>
      ) : filteredBookmarks.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center text-muted-foreground">
              <Search className="mx-auto mb-4 h-16 w-16 opacity-30" />
              <p className="mb-2 text-lg font-medium">No matching bookmarks</p>
              <p className="text-sm">Try a different search term</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredBookmarks.map((bookmark) => (
            <Card key={bookmark.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex items-center gap-2">
                      <Badge variant="outline">{bookmark.difficulty || "N/A"}</Badge>
                      <Badge variant="secondary">{bookmark.cognitive_level || "N/A"}</Badge>
                      {bookmark.question_status && (
                        <Badge
                          variant={
                            bookmark.question_status === "PUBLISHED" ? "default" : "secondary"
                          }
                        >
                          {bookmark.question_status}
                        </Badge>
                      )}
                    </div>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <p className="line-clamp-3 text-base leading-relaxed">
                        {bookmark.question_stem}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDeleteBookmark(bookmark.id)}
                      disabled={deletingId === bookmark.id}
                    >
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              {bookmark.notes && (
                <CardContent className="pt-0">
                  <div className="rounded-lg bg-muted p-3">
                    <p className="text-sm italic text-muted-foreground">
                      &quot;{bookmark.notes}&quot;
                    </p>
                  </div>
                </CardContent>
              )}
              <CardContent className="pt-0">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Saved {format(new Date(bookmark.created_at), "MMM d, yyyy")}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
