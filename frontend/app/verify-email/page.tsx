"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthPageLayout } from "@/components/auth/AuthPageLayout";
import { AuthCardShell, AuthCardFooter } from "@/components/auth/AuthCardShell";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error" | "idle">("idle");
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      verifyEmail(token);
    } else {
      setStatus("error");
      setError("No verification token provided");
    }
  }, [token]);

  const verifyEmail = async (verificationToken: string) => {
    setStatus("verifying");
    setError(null);

    try {
      const response = await fetch("/api/auth/verify-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: verificationToken }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorCode = data.error?.code;
        if (errorCode === "TOKEN_EXPIRED") {
          setError("This verification link has expired. Please request a new one.");
        } else if (errorCode === "TOKEN_INVALID") {
          setError("This verification link is invalid. Please request a new one.");
        } else {
          setError(data.error?.message || "Failed to verify email");
        }
        setStatus("error");
      } else {
        setStatus("success");
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setError(errorMessage);
      setStatus("error");
    }
  };

  const handleResend = () => {
    if (email) {
      router.push(`/resend-verification?email=${encodeURIComponent(email)}`);
    } else {
      router.push("/resend-verification");
    }
  };

  if (status === "verifying") {
    return (
      <AuthCardShell
        title="Verifying your email"
        subtitle="Please wait..."
        footer={<AuthCardFooter />}
      >
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-slate-600">Verifying your email address...</p>
        </div>
      </AuthCardShell>
    );
  }

  if (status === "success") {
    return (
      <AuthCardShell
        title="Email verified"
        subtitle="Your email has been successfully verified."
        footer={<AuthCardFooter />}
      >
        <div className="space-y-4">
          <InlineAlert variant="success" message="You can now log in to your account." />

          <Button
            onClick={() => router.push("/login")}
            className="w-full h-11 rounded-lg bg-primary font-semibold text-white hover:bg-primary/90"
          >
            Go to login
          </Button>

          <div className="text-center text-sm text-slate-600">
            <Link
              href="/login"
              className="font-medium text-primary hover:underline underline-offset-2"
            >
              Sign in →
            </Link>
          </div>
        </div>
      </AuthCardShell>
    );
  }

  return (
    <AuthCardShell
      title="Verification failed"
      subtitle="We couldn't verify your email address."
      footer={<AuthCardFooter />}
    >
      <div className="space-y-4">
        {error && (
          <InlineAlert
            variant="error"
            message={error}
            onDismiss={() => setError(null)}
          />
        )}

        <div className="space-y-3">
          <p className="text-sm text-slate-600">
            The verification link may have expired or is invalid. You can request a new verification email.
          </p>

          <Button
            onClick={handleResend}
            variant="outline"
            className="w-full"
          >
            Request new verification email
          </Button>
        </div>

        <div className="text-center text-sm text-slate-600 pt-4 border-t">
          <Link
            href="/login"
            className="font-medium text-primary hover:underline underline-offset-2"
          >
            Back to sign in
          </Link>
        </div>
      </div>
    </AuthCardShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <AuthPageLayout>
      <Suspense
        fallback={
          <AuthCardShell title="Verifying email" subtitle="Loading...">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          </AuthCardShell>
        }
      >
        <VerifyEmailForm />
      </Suspense>
    </AuthPageLayout>
  );
}
