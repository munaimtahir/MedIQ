import { redirect } from "next/navigation";
import { requireUser } from "@/lib/server/authGuard";

export default async function OnboardingLayout({ children }: { children: React.ReactNode }) {
  // Require authentication (but not onboarding completion)
  const user = await requireUser();

  // If user has already completed onboarding, redirect to dashboard
  if (user.onboarding_completed) {
    redirect("/student/dashboard");
  }

  // Render without sidebar for cleaner onboarding experience
  return <>{children}</>;
}
