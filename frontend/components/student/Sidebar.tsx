"use client";

import { memo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { authClient } from "@/lib/authClient";
import { notify } from "@/lib/notify";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useUnreadCount } from "@/lib/hooks/useNotifications";
import { useSidebarState } from "@/lib/hooks/useSidebarState";
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
  Network,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

// Feature flag check
const FEATURE_CONCEPT_EXPLORER_ENABLED =
  process.env.NEXT_PUBLIC_FEATURE_STUDENT_CONCEPT_EXPLORER === "true";

const baseStudentNavItems = [
  { href: "/student/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/student/notifications", label: "Notifications", icon: Bell },
  { href: "/student/blocks", label: "Blocks", icon: BookOpen },
  { href: "/student/practice/build", label: "Practice", icon: PlayCircle },
  { href: "/student/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/student/revision", label: "Revision", icon: RotateCcw },
  { href: "/student/bookmarks", label: "Bookmarks", icon: Bookmark },
  { href: "/student/settings", label: "Settings", icon: Settings },
];

// Conditionally add concepts link
const studentNavItems = FEATURE_CONCEPT_EXPLORER_ENABLED
  ? [
      ...baseStudentNavItems.slice(0, 3), // Dashboard, Notifications, Blocks
      { href: "/student/concepts", label: "Concepts", icon: Network },
      ...baseStudentNavItems.slice(3), // Rest
    ]
  : baseStudentNavItems;

export const StudentSidebar = memo(function StudentSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: unreadData } = useUnreadCount();
  const unreadCount = unreadData?.unread_count || 0;
  const { isCollapsed, toggle: toggleCollapse } = useSidebarState();

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

  const sidebarWidth = isCollapsed ? "w-16" : "w-64";

  return (
    <aside
      className={cn(
        "fixed left-0 top-16 z-40 flex h-[calc(100vh-4rem)] flex-col border-r bg-card transition-all duration-300",
        sidebarWidth,
      )}
    >
      <div className="flex h-full flex-col p-4">
        {/* Header with toggle */}
        <div className={cn("mb-6 flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
          {!isCollapsed && <h2 className="text-xl font-bold">Student Portal</h2>}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleCollapse}
            className="h-8 w-8"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto">
          {studentNavItems.map((item) => {
            const Icon = item.icon;
            // Check if current path matches or starts with the nav item href
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            const showBadge = item.href === "/student/notifications" && unreadCount > 0;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 transition-colors relative",
                  isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                  isCollapsed && "justify-center",
                )}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {!isCollapsed && <span>{item.label}</span>}
                {showBadge && !isCollapsed && (
                  <Badge
                    variant="destructive"
                    className="ml-auto h-5 min-w-5 flex items-center justify-center px-1.5 text-xs"
                  >
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </Badge>
                )}
                {showBadge && isCollapsed && (
                  <Badge
                    variant="destructive"
                    className="absolute -right-1 -top-1 h-4 min-w-4 flex items-center justify-center px-0.5 text-xs"
                  >
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </Badge>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Logout button - always visible at bottom */}
        <div className="mt-auto pt-4">
          <Button
            variant="outline"
            onClick={handleLogout}
            className={cn(
              "w-full justify-start gap-3",
              isCollapsed && "justify-center px-0",
            )}
            title={isCollapsed ? "Logout" : undefined}
          >
            <LogOut className="h-5 w-5 flex-shrink-0" />
            {!isCollapsed && <span>Logout</span>}
          </Button>
        </div>
      </div>
    </aside>
  );
});
