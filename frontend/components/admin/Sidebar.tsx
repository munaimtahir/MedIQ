"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
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

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <div className="min-h-screen w-64 border-r bg-card p-4">
      <h2 className="mb-6 text-xl font-bold">Admin Portal</h2>
      <nav className="space-y-1">
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
      </nav>
    </div>
  );
}
