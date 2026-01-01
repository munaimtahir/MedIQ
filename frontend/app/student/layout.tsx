import { StudentSidebar } from "@/components/student/Sidebar";
import { requireOnboardedUser } from "@/lib/server/authGuard";

export default async function StudentLayout({ children }: { children: React.ReactNode }) {
  // Enforce authentication AND onboarding completion
  // Redirects to /login if not authenticated
  // Redirects to /onboarding if onboarding not completed
  await requireOnboardedUser();

  return (
    <div className="flex min-h-screen">
      <StudentSidebar />
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
