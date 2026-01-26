import { AdminSidebarWrapper } from "@/components/admin/AdminSidebarWrapper";
import { ExamModeBanner } from "@/components/admin/ExamModeBanner";
import { FreezeUpdatesBanner } from "@/components/admin/FreezeUpdatesBanner";
import { requireRole } from "@/lib/server/authGuard";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  // Enforce authentication and ADMIN/REVIEWER role - redirects to /login or /403 if unauthorized
  await requireRole(["ADMIN", "REVIEWER"]);

  return (
    <div className="flex min-h-screen flex-col">
      <AdminSidebarWrapper>
        <ExamModeBanner />
        <FreezeUpdatesBanner />
        {children}
      </AdminSidebarWrapper>
    </div>
  );
}
