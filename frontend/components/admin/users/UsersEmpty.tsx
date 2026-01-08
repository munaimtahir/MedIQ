"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

interface UsersEmptyProps {
  onAddUser: () => void;
}

export function UsersEmpty({ onAddUser }: UsersEmptyProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center py-12">
        <p className="text-sm font-medium text-muted-foreground mb-2">No users found</p>
        <p className="text-xs text-muted-foreground mb-4">
          Try adjusting your search or filters
        </p>
        <Button variant="outline" size="sm" onClick={onAddUser}>
          <Plus className="h-4 w-4 mr-2" />
          Add User
        </Button>
      </CardContent>
    </Card>
  );
}
