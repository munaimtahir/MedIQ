"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { authClient } from "@/lib/authClient";
import { notify } from "@/lib/notify";
import { Button } from "@/components/ui/button";
import { useAdminSidebarState } from "@/lib/hooks/useAdminSidebarState";
import {
  LayoutDashboard,
  BookOpen,
  FileQuestion,
  CheckSquare,
  AlertCircle,
  FileText,
  Users,
  FileSearch,
  Settings,
  LogOut,
  Upload,
  Database,
  Clock,
  BarChart3,
  Beaker,
  Cpu,
  Gauge,
  Network,
  TrendingUp,
  Warehouse,
  BarChart,
  Medal,
  Mail,
  ChevronLeft,
  ChevronRight,
  Activity,
} from "lucide-react";

const adminNavItems = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/syllabus", label: "Syllabus", icon: BookOpen },
  { href: "/admin/questions", label: "Questions", icon: FileQuestion },
  { href: "/admin/review-queue", label: "Review Queue", icon: CheckSquare },
  { href: "/admin/issues", label: "Issues", icon: AlertCircle },
  { href: "/admin/mocks", label: "Mocks", icon: FileText },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/audit", label: "Audit", icon: FileSearch },
  { href: "/admin/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/admin/tag-quality", label: "Tag Quality", icon: AlertCircle },
  { href: "/admin/performance", label: "Performance", icon: Gauge },
  { href: "/admin/email", label: "Email", icon: Mail },
  { href: "/admin/notifications", label: "Notifications", icon: AlertCircle },
  { href: "/admin/algorithms", label: "Algorithms", icon: Cpu },
  { href: "/admin/system", label: "System", icon: Activity },
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

const intelligenceNavItems = [
  { href: "/admin/learning-ops", label: "Learning Ops", icon: Gauge },
  { href: "/admin/irt", label: "IRT", icon: Beaker },
  { href: "/admin/rank", label: "Rank", icon: TrendingUp },
  { href: "/admin/ranking", label: "Ranking Ops", icon: Medal },
  { href: "/admin/graph-revision", label: "Graph Revision", icon: Network },
  { href: "/admin/search", label: "Search", icon: FileSearch },
  { href: "/admin/warehouse", label: "Warehouse", icon: Warehouse },
  { href: "/admin/cohorts", label: "Cohorts", icon: BarChart },
];

const evaluationNavItems = [
  { href: "/admin/evaluation", label: "Evaluation Harness", icon: BarChart3 },
];

const importNavItems = [
  { href: "/admin/import/questions", label: "Upload Questions", icon: Upload },
  { href: "/admin/import/schemas", label: "Import Schemas", icon: Database },
  { href: "/admin/import/jobs", label: "Recent Jobs", icon: Clock },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isCollapsed, toggle: toggleCollapse } = useAdminSidebarState();

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
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-card transition-all duration-300",
        sidebarWidth,
      )}
      data-testid="admin-sidebar"
    >
      <div className="flex h-full flex-col p-4">
        {/* Header with toggle */}
        <div className={cn("mb-6 flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
          {!isCollapsed && <h2 className="text-xl font-bold">Admin Portal</h2>}
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

        {/* Navigation - fixed height, no scroll */}
        <nav className="flex-1 space-y-1 overflow-hidden">
        {adminNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                isCollapsed && "justify-center",
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Intelligence Section */}
        {!isCollapsed && (
          <div className="pb-2 pt-4">
            <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Intelligence
            </h3>
          </div>
        )}
        {intelligenceNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                isCollapsed && "justify-center",
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Import Section */}
        {!isCollapsed && (
          <div className="pb-2 pt-4">
            <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Import
            </h3>
          </div>
        )}
        {importNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                isCollapsed && "justify-center",
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Evaluation Section */}
        {!isCollapsed && (
          <div className="pb-2 pt-4">
            <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Evaluation
            </h3>
          </div>
        )}
        {evaluationNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-muted",
                isCollapsed && "justify-center",
              )}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {!isCollapsed && <span>{item.label}</span>}
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
            data-testid="logout-button"
          >
            <LogOut className="h-5 w-5 flex-shrink-0" />
            {!isCollapsed && <span>Logout</span>}
          </Button>
        </div>
      </div>
    </aside>
  );
}
