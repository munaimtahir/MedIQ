import { redirect } from "next/navigation";
import { getUser } from "@/lib/server/authGuard";
import { LandingClient } from "@/components/landing/LandingClient";

export default async function HomePage() {
  // Server-side auth check
  const user = await getUser().catch(() => null);
  
  if (user) {
    // Redirect authenticated users to their dashboard
    if (user.role === "STUDENT") {
      redirect("/student/dashboard");
    } else if (user.role === "ADMIN" || user.role === "REVIEWER") {
      redirect("/admin");
    }
  }
  
  return <LandingClient />;
}
