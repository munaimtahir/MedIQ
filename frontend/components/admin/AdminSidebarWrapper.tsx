"use client";

import { AdminSidebar } from "./Sidebar";
import { useAdminSidebarState } from "@/lib/hooks/useAdminSidebarState";

export function AdminSidebarWrapper({ children }: { children: React.ReactNode }) {
  const { isCollapsed } = useAdminSidebarState();
  const sidebarWidth = isCollapsed ? 64 : 256; // 64px when collapsed, 256px when expanded

  return (
    <div className="flex flex-1">
      <AdminSidebar />
      <main
        className="flex-1 p-8 transition-all duration-300"
        style={{ marginLeft: `${sidebarWidth}px` }}
      >
        {children}
      </main>
    </div>
  );
}
