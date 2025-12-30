"use client";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { SignupCard } from "@/components/auth/SignupCard";
import { SignupRightPanel } from "@/components/auth/SignupRightPanel";

export default function SignupPage() {
  return (
    <AuthLayout rightPanel={<SignupRightPanel />}>
      <SignupCard />
    </AuthLayout>
  );
}
