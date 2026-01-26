"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bell, Settings, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useNotifications } from "@/lib/notifications/hooks";
import { isUnread } from "@/lib/notifications/utils";
import { useUserStore, selectUser, selectFetchUser } from "@/store/userStore";
import { authClient } from "@/lib/authClient";
import { notify } from "@/lib/notify";

export function StudentHeader() {
  const router = useRouter();
  const user = useUserStore(selectUser);
  const fetchUser = useUserStore(selectFetchUser);
  const { items: notifications } = useNotifications();
  const unreadCount = notifications.filter((item) => isUnread(item)).length;

  // Fetch user data on mount if not already loaded
  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, [user, fetchUser]);

  const handleLogout = async () => {
    try {
      await authClient.logout();
      notify.success("Logged out", "You have been logged out successfully.");
      router.push("/login");
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      notify.error("Logout failed", errorMessage);
    }
  };

  const userInitials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "U";

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4">
        {/* Logo/Branding - optional, can be removed if not needed */}
        <div className="flex items-center gap-2">
          <Link href="/student/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
              <span className="text-sm font-bold text-white">E</span>
            </div>
            <span className="hidden font-semibold sm:inline-block">Exam Prep</span>
          </Link>
        </div>

        {/* Right side: Notifications + User Menu */}
        <div className="flex items-center gap-2">
          {/* Notifications Bell */}
          <Link href="/student/notifications">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <Badge
                  variant="destructive"
                  className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full p-0 text-xs"
                >
                  {unreadCount > 9 ? "9+" : unreadCount}
                </Badge>
              )}
            </Button>
          </Link>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="relative h-10 w-10 overflow-hidden rounded-full focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90">
                  <span className="text-sm font-semibold">{userInitials}</span>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.name || "User"}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/student/settings" className="flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
