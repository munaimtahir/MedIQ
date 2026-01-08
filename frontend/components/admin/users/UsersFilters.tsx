"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";

interface UsersFiltersProps {
  search: string;
  role: string | undefined;
  status: string | undefined;
  onSearchChange: (value: string) => void;
  onRoleChange: (value: string | undefined) => void;
  onStatusChange: (value: string | undefined) => void;
}

export function UsersFilters({
  search,
  role,
  status,
  onSearchChange,
  onRoleChange,
  onStatusChange,
}: UsersFiltersProps) {
  const [searchInput, setSearchInput] = useState(search);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(searchInput);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput, onSearchChange]);

  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end">
      <div className="flex-1 space-y-2">
        <Label htmlFor="search">Search</Label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="search"
            placeholder="Search by name or email..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>
      <div className="space-y-2 md:w-48">
        <Label htmlFor="role">Role</Label>
        <Select value={role || "all"} onValueChange={(v) => onRoleChange(v === "all" ? undefined : v)}>
          <SelectTrigger id="role">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            <SelectItem value="STUDENT">Student</SelectItem>
            <SelectItem value="ADMIN">Admin</SelectItem>
            <SelectItem value="REVIEWER">Reviewer</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-2 md:w-48">
        <Label htmlFor="status">Status</Label>
        <Select value={status || "all"} onValueChange={(v) => onStatusChange(v === "all" ? undefined : v)}>
          <SelectTrigger id="status">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
