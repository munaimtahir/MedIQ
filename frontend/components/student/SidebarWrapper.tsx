"use client";

import { StudentSidebar } from "./Sidebar";
import { useSidebarState } from "@/lib/hooks/useSidebarState";

export function SidebarWrapper({ children }: { children: React.ReactNode }) {
  const { isCollapsed } = useSidebarState();
  const sidebarWidth = isCollapsed ? 64 : 256; // 64px when collapsed, 256px when expanded

  return (
    <div className="flex flex-1">
      <StudentSidebar />
      <main
        className="flex-1 p-8 transition-all duration-300"
        style={{ marginLeft: `${sidebarWidth}px` }}
      >
        {children}
      </main>
    </div>
  );
}
