"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthPageLayout } from "@/components/auth/AuthPageLayout";
import { AuthCardShell, AuthCardFooter } from "@/components/auth/AuthCardShell";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { PasswordField } from "@/components/auth/PasswordField";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errors, setErrors] = useState<{
    password?: string;
    confirmPassword?: string;
    general?: string;
  }>({});

  useEffect(() => {
    if (!token) {
      setErrors({ general: "No reset token provided" });
    }
  }, [token]);

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 10) {
      newErrors.password = "Password must be at least 10 characters";
    } else if (!/[a-zA-Z]/.test(password)) {
      newErrors.password = "Password must contain at least one letter";
    } else if (!/[0-9]/.test(password)) {
      newErrors.password = "Password must contain at least one number";
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      setErrors({ general: "No reset token provided" });
      return;
    }

    if (!validate()) return;

    setLoading(true);
    setErrors({});

    try {
      const response = await fetch("/api/v1/auth/password-reset/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          token,
          new_password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        const errorCode = data.error?.code;
        if (errorCode === "TOKEN_EXPIRED") {
          setErrors({ general: "This reset link has expired. Please request a new one." });
        } else if (errorCode === "TOKEN_INVALID") {
          setErrors({ general: "This reset link is invalid. Please request a new one." });
        } else if (errorCode === "TOKEN_USED") {
          setErrors({
            general: "This reset link has already been used. Please request a new one.",
          });
        } else {
          setErrors({ general: data.error?.message || "Failed to reset password" });
        }
      } else {
        setSuccess(true);
        // Show toast and redirect after a brief delay
        setTimeout(() => {
          router.push("/login?reset=success");
        }, 1500);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setErrors({ general: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <AuthCardShell
        title="Password updated"
        subtitle="Your password has been successfully reset."
        footer={<AuthCardFooter />}
      >
        <div className="space-y-4">
          <InlineAlert variant="success" message="You can now log in with your new password." />

          <Button
            onClick={() => router.push("/login")}
            className="h-11 w-full rounded-lg bg-primary font-semibold text-white hover:bg-primary/90"
          >
            Go to login
          </Button>

          <div className="text-center text-sm text-slate-600">
            <Link
              href="/login"
              className="font-medium text-primary underline-offset-2 hover:underline"
            >
              Sign in →
            </Link>
          </div>
        </div>
      </AuthCardShell>
    );
  }

  if (!token) {
    return (
      <AuthCardShell
        title="Invalid reset link"
        subtitle="No reset token provided."
        footer={<AuthCardFooter />}
      >
        <div className="space-y-4">
          {errors.general && (
            <InlineAlert
              variant="error"
              message={errors.general}
              onDismiss={() => setErrors((prev) => ({ ...prev, general: undefined }))}
            />
          )}

          <div className="space-y-2 text-center text-sm text-slate-600">
            <p>Please use the link from your password reset email.</p>
            <Link
              href="/forgot-password"
              className="font-medium text-primary underline-offset-2 hover:underline"
            >
              Request a new reset link
            </Link>
          </div>

          <div className="border-t pt-4 text-center text-sm text-slate-600">
            <Link
              href="/login"
              className="font-medium text-primary underline-offset-2 hover:underline"
            >
              Back to sign in
            </Link>
          </div>
        </div>
      </AuthCardShell>
    );
  }

  return (
    <AuthCardShell
      title="Reset your password"
      subtitle="Enter your new password below."
      footer={<AuthCardFooter />}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Password Field */}
        <div data-animate>
          <PasswordField
            id="password"
            label="New password"
            value={password}
            onChange={(value) => {
              setPassword(value);
              if (errors.password) {
                setErrors((prev) => ({ ...prev, password: undefined }));
              }
            }}
            placeholder="Enter your new password"
            error={errors.password}
            helperText="Use at least 10 characters with letters and numbers."
            autoComplete="new-password"
          />
        </div>

        {/* Confirm Password Field */}
        <div data-animate>
          <PasswordField
            id="confirmPassword"
            label="Confirm password"
            value={confirmPassword}
            onChange={(value) => {
              setConfirmPassword(value);
              if (errors.confirmPassword) {
                setErrors((prev) => ({ ...prev, confirmPassword: undefined }));
              }
            }}
            placeholder="Confirm your new password"
            error={errors.confirmPassword}
            autoComplete="new-password"
          />
        </div>

        {/* Error Alert */}
        {errors.general && (
          <div data-animate>
            <InlineAlert
              variant="error"
              message={errors.general}
              onDismiss={() => setErrors((prev) => ({ ...prev, general: undefined }))}
            />
          </div>
        )}

        {/* Submit Button */}
        <div data-animate>
          <Button
            type="submit"
            disabled={loading}
            className="h-11 w-full rounded-lg bg-primary font-semibold text-white transition-all duration-200 hover:bg-primary/90"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Resetting password...
              </>
            ) : (
              "Reset password"
            )}
          </Button>
        </div>

        {/* Back to Login */}
        <div data-animate className="text-center text-sm text-slate-600">
          Remember your password?{" "}
          <Link
            href="/login"
            className="font-medium text-primary underline-offset-2 hover:underline"
          >
            Sign in
          </Link>
        </div>
      </form>
    </AuthCardShell>
  );
}

export default function ResetPasswordPage() {
  return (
    <AuthPageLayout>
      <Suspense
        fallback={
          <AuthCardShell title="Reset password" subtitle="Loading...">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          </AuthCardShell>
        }
      >
        <ResetPasswordForm />
      </Suspense>
    </AuthPageLayout>
  );
}
