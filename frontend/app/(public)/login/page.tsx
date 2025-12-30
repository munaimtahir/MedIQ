"use client";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { LoginCard } from "@/components/auth/LoginCard";
import { LoginRightPanel } from "@/components/auth/LoginRightPanel";

export default function LoginPage() {
  return (
    <AuthLayout rightPanel={<LoginRightPanel />}>
      <LoginCard />
    </AuthLayout>
  );
}
