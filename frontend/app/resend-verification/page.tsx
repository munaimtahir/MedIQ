"use client";

import React, { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthPageLayout } from "@/components/auth/AuthPageLayout";
import { AuthCardShell, AuthCardFooter } from "@/components/auth/AuthCardShell";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

function ResendVerificationForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailParam = searchParams.get("email");

  const [email, setEmail] = useState(emailParam || "");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError("Please enter your email address");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error?.message || "Failed to resend verification email");
      } else {
        setSuccess(true);
        setError(null);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <AuthCardShell
        title="Verification email sent"
        subtitle="Check your inbox for the verification link."
        footer={<AuthCardFooter />}
      >
        <div className="space-y-4">
          <InlineAlert
            variant="success"
            message="If an account exists and is unverified, you will receive an email shortly."
          />

          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              We've sent a verification link to <strong>{email}</strong>. Please check your inbox and click the link to verify your email address.
            </p>
            <p className="text-sm text-slate-600">
              The verification link will expire in 24 hours. If you don't see the email, check your spam folder.
            </p>
          </div>

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
      title="Resend verification email"
      subtitle="Enter your email address to receive a new verification link."
      footer={<AuthCardFooter />}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <InlineAlert
            variant="error"
            message={error}
            onDismiss={() => setError(null)}
          />
        )}

        <div className="space-y-2">
          <Label htmlFor="email">Email address</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
            autoFocus
            className="h-11"
          />
        </div>

        <Button
          type="submit"
          disabled={loading || !email.trim()}
          className="w-full h-11 rounded-lg bg-primary font-semibold text-white hover:bg-primary/90"
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Sending...
            </>
          ) : (
            "Resend verification email"
          )}
        </Button>

        <div className="text-center text-sm text-slate-600 pt-4 border-t">
          <Link
            href="/login"
            className="font-medium text-primary hover:underline underline-offset-2"
          >
            Back to sign in
          </Link>
        </div>
      </form>
    </AuthCardShell>
  );
}

export default function ResendVerificationPage() {
  return (
    <AuthPageLayout>
      <Suspense
        fallback={
          <AuthCardShell title="Resend verification" subtitle="Loading...">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          </AuthCardShell>
        }
      >
        <ResendVerificationForm />
      </Suspense>
    </AuthPageLayout>
  );
}
