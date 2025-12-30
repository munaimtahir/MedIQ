'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Bookmark } from 'lucide-react';

export default function BookmarksPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Bookmarks</h1>
        <p className="text-muted-foreground">Save questions for later review</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Saved Questions</CardTitle>
          <CardDescription>Questions you&apos;ve bookmarked</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Bookmark className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No bookmarks yet. Mark questions during practice to save them here.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

