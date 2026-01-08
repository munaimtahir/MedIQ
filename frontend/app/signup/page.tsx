"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authClient } from "@/lib/authClient";
import { routeAfterAuth } from "@/lib/routeAfterAuth";
import { AuthPageLayout } from "@/components/auth/AuthPageLayout";
import { AuthCardShell, AuthCardFooter } from "@/components/auth/AuthCardShell";
import { OAuthButtons } from "@/components/auth/OAuthButtons";
import { DividerWithText } from "@/components/auth/DividerWithText";
import { PasswordField } from "@/components/auth/PasswordField";
import { InlineAlert } from "@/components/auth/InlineAlert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [resending, setResending] = useState(false);
  const [errors, setErrors] = useState<{
    name?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
    general?: string;
  }>({});

  // Check if user is already authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const result = await authClient.me();
        if (result.data?.user) {
          // Already authenticated, route appropriately
          await routeAfterAuth(router.push);
        }
      } catch {
        // Not authenticated, stay on page
      }
    };
    checkAuth();
  }, [router]);

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Full name is required";
    }

    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      newErrors.email = "Please enter a valid email";
    }

    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    } else if (!/[a-zA-Z]/.test(formData.password)) {
      newErrors.password = "Password must contain at least one letter";
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = "Password must contain at least one number";
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field: keyof typeof formData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    setErrors({});

    try {
      const result = await authClient.signup({
        name: formData.name.trim(),
        email: formData.email.trim(),
        password: formData.password,
      });

      if (result.error) {
        if (result.error.code === "CONFLICT") {
          setErrors({ 
            email: "An account with this email already exists",
            general: "An account with this email already exists. Please log in instead."
          });
        } else if (result.error.code === "RATE_LIMITED") {
          setErrors({
            general: "Too many signup attempts. Please try again later.",
          });
        } else {
          setErrors({
            general: result.error.message || "Signup failed. Please try again.",
          });
        }
        return;
      }

      if (result.data?.user) {
        // Success - show verification message (don't route, user needs to verify email)
        setSuccess(true);
        setErrors({});
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setErrors({ general: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!formData.email.trim()) return;

    setResending(true);
    setErrors({});

    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: formData.email.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErrors({ general: data.error?.message || "Failed to resend verification email" });
      } else {
        // Show success message
        setErrors({});
        // You could show a toast here
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setErrors({ general: errorMessage });
    } finally {
      setResending(false);
    }
  };

  // Show success state after signup
  if (success) {
    const isDev = process.env.NODE_ENV === "development";
    return (
      <AuthPageLayout>
        <AuthCardShell
          title="Check your email"
          subtitle="We've sent a verification link to your email address."
          footer={<AuthCardFooter />}
        >
          <div className="space-y-4">
            <div data-animate>
              <InlineAlert
                variant="success"
                message="Account created successfully! Please verify your email to continue."
              />
            </div>

            <div data-animate className="space-y-3">
              <p className="text-sm text-slate-600">
                Click the link in the email to verify your account. The link will expire in 24 hours.
              </p>

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

              <div className="flex flex-col gap-2">
                <Button
                  onClick={handleResendVerification}
                  disabled={resending}
                  variant="outline"
                  className="w-full"
                >
                  {resending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    "Resend verification email"
                  )}
                </Button>

                <p className="text-xs text-slate-500 text-center">
                  Didn't receive the email? Check your spam folder.
                </p>
              </div>
            </div>

            <div data-animate className="text-center text-sm text-slate-600 pt-4 border-t">
              <Link
                href="/login"
                className="font-medium text-primary hover:underline underline-offset-2"
              >
                Back to sign in
              </Link>
            </div>
          </div>
        </AuthCardShell>
      </AuthPageLayout>
    );
  }

  return (
    <AuthPageLayout>
      <AuthCardShell
        title="Create your account"
        subtitle="You'll verify your email in the next step."
        footer={<AuthCardFooter />}
      >
        {/* OAuth Buttons */}
        <div data-animate>
          <OAuthButtons mode="signup" loading={loading} />
        </div>

        {/* Divider */}
        <div data-animate>
          <DividerWithText text="or sign up with email" />
        </div>

        {/* Signup Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Full Name Field */}
          <div data-animate className="space-y-2">
            <Label htmlFor="name" className="text-slate-700 font-medium">
              Full name
            </Label>
            <Input
              id="name"
              type="text"
              placeholder="Enter your full name"
              value={formData.name}
              onChange={(e) => handleChange("name", e.target.value)}
              autoComplete="name"
              disabled={loading}
              className={`h-11 rounded-lg border-slate-200 bg-white focus:border-primary focus:ring-primary ${
                errors.name ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
              }`}
            />
            {errors.name && (
              <p className="text-sm text-red-600">{errors.name}</p>
            )}
          </div>

          {/* Email Field */}
          <div data-animate className="space-y-2">
            <Label htmlFor="email" className="text-slate-700 font-medium">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={formData.email}
              onChange={(e) => handleChange("email", e.target.value)}
              autoComplete="email"
              disabled={loading}
              className={`h-11 rounded-lg border-slate-200 bg-white focus:border-primary focus:ring-primary ${
                errors.email ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
              }`}
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email}</p>
            )}
          </div>

          {/* Password Field */}
          <div data-animate>
            <PasswordField
              id="password"
              label="Password"
              value={formData.password}
              onChange={(value) => handleChange("password", value)}
              placeholder="Create a password"
              error={errors.password}
              helperText="Use at least 8 characters."
              autoComplete="new-password"
            />
          </div>

          {/* Confirm Password Field */}
          <div data-animate>
            <PasswordField
              id="confirmPassword"
              label="Confirm password"
              value={formData.confirmPassword}
              onChange={(value) => handleChange("confirmPassword", value)}
              placeholder="Confirm your password"
              error={errors.confirmPassword}
              autoComplete="new-password"
            />
          </div>

          {/* Error Alert */}
          {errors.general && (
            <div data-animate className="space-y-3">
              <InlineAlert
                variant="error"
                message={errors.general}
                onDismiss={() => setErrors((prev) => ({ ...prev, general: undefined }))}
              />
              {errors.general.includes("already exists") && (
                <Button
                  type="button"
                  onClick={() => router.push(`/login?email=${encodeURIComponent(formData.email.trim())}`)}
                  variant="default"
                  className="w-full"
                >
                  Go to Login
                </Button>
              )}
            </div>
          )}

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
                  Creating account...
                </>
              ) : (
                "Create account"
              )}
            </Button>
          </div>

          {/* Sign In Link */}
          <div data-animate className="text-center text-sm text-slate-600">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-medium text-primary hover:underline underline-offset-2"
            >
              Sign in
            </Link>
          </div>
        </form>
      </AuthCardShell>
    </AuthPageLayout>
  );
}
