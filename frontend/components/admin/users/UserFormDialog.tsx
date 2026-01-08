"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { User, UserCreate, UserUpdate } from "@/lib/admin/users/types";

interface UserFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user?: User | null;
  onSave: (data: UserCreate | UserUpdate) => Promise<void>;
}

export function UserFormDialog({
  open,
  onOpenChange,
  user,
  onSave,
}: UserFormDialogProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"STUDENT" | "ADMIN" | "REVIEWER">("STUDENT");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setEmail(user.email);
      setRole(user.role);
      setIsActive(user.is_active);
    } else {
      setName("");
      setEmail("");
      setRole("STUDENT");
      setIsActive(true);
    }
    setError(null);
  }, [user, open]);

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (!email.trim()) {
      setError("Email is required");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (user) {
        await onSave({
          name: name.trim(),
          role,
          is_active: isActive,
        } as UserUpdate);
      } else {
        await onSave({
          name: name.trim(),
          email: email.trim(),
          role,
          is_active: isActive,
        } as UserCreate);
      }
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{user ? "Edit User" : "Add User"}</DialogTitle>
          <DialogDescription>
            {user
              ? "Update user information"
              : "Create a new user account. A password reset email will be sent."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email *</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              disabled={!!user}
            />
            {user && (
              <p className="text-xs text-muted-foreground">Email cannot be changed</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">Role *</Label>
            <Select value={role} onValueChange={(v) => setRole(v as "STUDENT" | "ADMIN" | "REVIEWER")}>
              <SelectTrigger id="role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="STUDENT">Student</SelectItem>
                <SelectItem value="ADMIN">Admin</SelectItem>
                <SelectItem value="REVIEWER">Reviewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center space-x-2">
            <Switch
              id="is_active"
              checked={isActive}
              onCheckedChange={setIsActive}
            />
            <Label htmlFor="is_active">Active</Label>
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
