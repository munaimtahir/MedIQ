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
  { href: "/admin/settings", label: "Settings", icon: Settings },
];

const importNavItems = [
  { href: "/admin/import/questions", label: "Upload Questions", icon: Upload },
  { href: "/admin/import/schemas", label: "Import Schemas", icon: Database },
  { href: "/admin/import/jobs", label: "Recent Jobs", icon: Clock },
];

export function AdminSidebar() {
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
      <h2 className="mb-6 text-xl font-bold">Admin Portal</h2>
      <nav className="flex-1 space-y-1 overflow-y-auto">
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
              )}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}

        {/* Import Section */}
        <div className="pb-2 pt-4">
          <h3 className="px-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Import
          </h3>
        </div>
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
