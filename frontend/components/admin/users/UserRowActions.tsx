"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, Edit, Power, PowerOff, Key } from "lucide-react";
import { User } from "@/lib/admin/users/types";

interface UserRowActionsProps {
  user: User;
  currentUserId: string | null;
  onEdit: () => void;
  onEnable: () => void;
  onDisable: () => void;
  onPasswordReset: () => void;
}

export function UserRowActions({
  user,
  currentUserId,
  onEdit,
  onEnable,
  onDisable,
  onPasswordReset,
}: UserRowActionsProps) {
  const isSelf = currentUserId === user.id;
  const canDisable = !isSelf;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={onEdit}>
          <Edit className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {user.is_active ? (
          <DropdownMenuItem
            onClick={onDisable}
            disabled={!canDisable}
            className={!canDisable ? "opacity-50" : ""}
          >
            <PowerOff className="mr-2 h-4 w-4" />
            Disable
            {!canDisable && " (Cannot disable self)"}
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={onEnable}>
            <Power className="mr-2 h-4 w-4" />
            Enable
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onPasswordReset}>
          <Key className="mr-2 h-4 w-4" />
          Send Password Reset
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
