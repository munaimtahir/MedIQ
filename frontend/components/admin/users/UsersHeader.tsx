"use client";

import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

interface UsersHeaderProps {
  onAddUser: () => void;
}

export function UsersHeader({ onAddUser }: UsersHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold">Users</h1>
        <p className="text-muted-foreground">Manage platform users and access control</p>
      </div>
      <Button onClick={onAddUser}>
        <Plus className="h-4 w-4 mr-2" />
        Add User
      </Button>
    </div>
  );
}
