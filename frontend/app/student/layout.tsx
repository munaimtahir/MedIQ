import { StudentHeader } from "@/components/student/Header";
import { SidebarWrapper } from "@/components/student/SidebarWrapper";
import { requireOnboardedUser } from "@/lib/server/authGuard";

export default async function StudentLayout({ children }: { children: React.ReactNode }) {
  // Enforce authentication AND onboarding completion
  // Redirects to /login if not authenticated
  // Redirects to /onboarding if onboarding not completed
  await requireOnboardedUser();

  return (
    <div className="flex min-h-screen flex-col">
      <StudentHeader />
      <SidebarWrapper>{children}</SidebarWrapper>
    </div>
  );
}
