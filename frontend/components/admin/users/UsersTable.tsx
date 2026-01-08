"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { User } from "@/lib/admin/users/types";
import { UserRowActions } from "./UserRowActions";

interface UsersTableProps {
  users: User[];
  currentUserId: string | null;
  onEdit: (user: User) => void;
  onEnable: (user: User) => void;
  onDisable: (user: User) => void;
  onPasswordReset: (user: User) => void;
}

export function UsersTable({
  users,
  currentUserId,
  onEdit,
  onEnable,
  onDisable,
  onPasswordReset,
}: UsersTableProps) {
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Last Login</TableHead>
            <TableHead className="w-[70px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.length === 0 ? (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                No users found
              </TableCell>
            </TableRow>
          ) : (
            users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <Badge
                    variant={
                      user.role === "ADMIN"
                        ? "default"
                        : user.role === "REVIEWER"
                        ? "secondary"
                        : "outline"
                    }
                  >
                    {user.role}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={user.is_active ? "default" : "secondary"}>
                    {user.is_active ? "Active" : "Disabled"}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(user.created_at)}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {user.last_login_at ? formatDate(user.last_login_at) : "—"}
                </TableCell>
                <TableCell>
                  <UserRowActions
                    user={user}
                    currentUserId={currentUserId}
                    onEdit={() => onEdit(user)}
                    onEnable={() => onEnable(user)}
                    onDisable={() => onDisable(user)}
                    onPasswordReset={() => onPasswordReset(user)}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
