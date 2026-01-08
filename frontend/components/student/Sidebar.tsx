"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { authClient } from "@/lib/authClient";
import { notify } from "@/lib/notify";
import { Button } from "@/components/ui/button";
import {
  LayoutDashboard,
  BookOpen,
  PlayCircle,
  BarChart3,
  Bookmark,
  Settings,
  RotateCcw,
  LogOut,
  Bell,
} from "lucide-react";

const studentNavItems = [
  { href: "/student/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/student/notifications", label: "Notifications", icon: Bell },
  { href: "/student/blocks", label: "Blocks", icon: BookOpen },
  { href: "/student/practice/build", label: "Practice", icon: PlayCircle },
  { href: "/student/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/student/revision", label: "Revision", icon: RotateCcw },
  { href: "/student/bookmarks", label: "Bookmarks", icon: Bookmark },
  { href: "/student/settings", label: "Settings", icon: Settings },
];

export function StudentSidebar() {
  const pathname = usePathname();
  const router = useRouter();

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

  return (
    <div className="flex min-h-screen w-64 flex-col border-r bg-card p-4">
      <h2 className="mb-6 text-xl font-bold">Student Portal</h2>
      <nav className="flex-1 space-y-1">
        {studentNavItems.map((item) => {
          const Icon = item.icon;
          // Check if current path matches or starts with the nav item href
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted",
              )}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto pt-4">
        <Button variant="outline" onClick={handleLogout} className="w-full justify-start gap-3">
          <LogOut className="h-5 w-5" />
          <span>Logout</span>
        </Button>
      </div>
    </div>
  );
}
