"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AuthPageLayout } from "@/components/auth/AuthPageLayout";
import { AuthCardShell, AuthCardFooter } from "@/components/auth/AuthCardShell";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validate = (): boolean => {
    if (!email.trim()) {
      setError("Email is required");
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError("Please enter a valid email");
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error?.message || "Failed to send password reset email");
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

  const isDev = process.env.NODE_ENV === "development";

  return (
    <AuthPageLayout>
      <AuthCardShell
        title="Reset your password"
        subtitle="Enter your email address and we'll send you a reset link."
        footer={<AuthCardFooter />}
      >
        {success ? (
          <div className="space-y-4">
            <InlineAlert
              variant="success"
              message="If an account exists with this email, you will receive a password reset link shortly."
            />

            {isDev && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-800 font-medium mb-1">Development Mode</p>
                <a
                  href="http://localhost:8025"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  Open Mailpit inbox →
                </a>
              </div>
            )}

            <div className="space-y-3">
              <p className="text-sm text-slate-600">
                Check your email for the password reset link. The link will expire in 30 minutes.
              </p>

              <p className="text-xs text-slate-500">
                Didn't receive the email? Check your spam folder or try again.
              </p>
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
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div data-animate className="space-y-2">
              <Label htmlFor="email" className="text-slate-700 font-medium">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setError(null);
                }}
                autoComplete="email"
                disabled={loading}
                className={`h-11 rounded-lg border-slate-200 bg-white focus:border-primary focus:ring-primary ${
                  error ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
                }`}
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>

            {/* Submit Button */}
            <div data-animate>
              <Button
                type="submit"
                disabled={loading}
                className="w-full h-11 rounded-lg bg-primary font-semibold text-white hover:bg-primary/90 transition-all duration-200"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  "Send reset link"
                )}
              </Button>
            </div>

            {/* Back to Login */}
            <div data-animate className="text-center text-sm text-slate-600">
              Remember your password?{" "}
              <Link
                href="/login"
                className="font-medium text-primary hover:underline underline-offset-2"
              >
                Sign in
              </Link>
            </div>
          </form>
        )}
      </AuthCardShell>
    </AuthPageLayout>
  );
}
