"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
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

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectParam = searchParams.get("redirect");
  const oauthError = searchParams.get("error");
  const oauthProvider = searchParams.get("provider");
  const linkRequired = searchParams.get("link_required");
  const linkToken = searchParams.get("link_token");
  const linkEmail = searchParams.get("email");
  const mfaRequired = searchParams.get("mfa");

  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    general?: string;
  }>({});

  // OAuth error messages mapping
  const oauthErrorMessages: Record<string, string> = {
    OAUTH_STATE_INVALID: "Authentication session expired. Please try again.",
    OAUTH_TOKEN_EXCHANGE_FAILED: "Failed to complete sign-in. Please try again.",
    OAUTH_ID_TOKEN_INVALID: "Invalid authentication response. Please try again.",
    OAUTH_CODE_INVALID: "Authentication code expired. Please try again.",
    ACCOUNT_INACTIVE: "Your account has been deactivated. Please contact support.",
    VALIDATION_ERROR: "Authentication failed. Please try again.",
    OAUTH_EXCHANGE_FAILED: "Failed to complete sign-in. Please try again.",
    OAUTH_NO_TOKENS: "Authentication incomplete. Please try again.",
  };

  // Handle OAuth errors on mount
  useEffect(() => {
    if (oauthError) {
      const message = oauthErrorMessages[oauthError] || `Authentication failed: ${oauthError}`;
      setErrors({ general: message });
      // Clean URL without reloading
      const url = new URL(window.location.href);
      url.searchParams.delete("error");
      url.searchParams.delete("provider");
      window.history.replaceState({}, "", url.toString());
    }
  }, [oauthError]);

  // Handle link required - pre-fill email
  useEffect(() => {
    if (linkRequired && linkEmail) {
      setEmail(linkEmail);
      setErrors({
        general: `An account with ${linkEmail} already exists. Enter your password to link your ${oauthProvider || "OAuth"} account.`,
      });
    }
  }, [linkRequired, linkEmail, oauthProvider]);

  // Handle MFA redirect from OAuth
  useEffect(() => {
    if (mfaRequired === "true") {
      setErrors({
        general: "Multi-factor authentication is required. This feature is coming soon.",
      });
      // Clean URL
      const url = new URL(window.location.href);
      url.searchParams.delete("mfa");
      url.searchParams.delete("mfa_token");
      url.searchParams.delete("method");
      window.history.replaceState({}, "", url.toString());
    }
  }, [mfaRequired]);

  // Check if user is already authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const result = await authClient.me();
        if (result.data?.user) {
          // Already authenticated, route appropriately
          await routeAfterAuth(router.push, { redirectParam });
        }
      } catch {
        // Not authenticated, stay on page
      }
    };
    checkAuth();
  }, [router, redirectParam]);

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      newErrors.email = "Please enter a valid email";
    }

    if (!password) {
      newErrors.password = "Password is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    setErrors({});

    try {
      const result = await authClient.login({
        email: email.trim(),
        password,
      });

      if (result.error) {
        // Handle specific error codes
        if (result.error.code === "RATE_LIMITED") {
          const retryAfter = (result.error.details as { retry_after_seconds?: number })
            ?.retry_after_seconds;
          setErrors({
            general: `Too many login attempts. Please try again in ${retryAfter || "a few"} seconds.`,
          });
        } else if (result.error.code === "ACCOUNT_LOCKED") {
          const lockExpires = (result.error.details as { lock_expires_in?: number })
            ?.lock_expires_in;
          setErrors({
            general: `Account temporarily locked. Please try again in ${lockExpires || "a few"} minutes.`,
          });
        } else {
          setErrors({
            general: result.error.message || "Invalid email or password",
          });
        }
        return;
      }

      if (result.mfa_required) {
        // TODO: Handle MFA flow when implemented
        setErrors({
          general: "Multi-factor authentication is required. This feature is coming soon.",
        });
        return;
      }

      if (result.data?.user) {
        // Success - route to appropriate destination
        await routeAfterAuth(router.push, { redirectParam });
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setErrors({ general: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  const clearFieldError = (field: "email" | "password") => {
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  return (
    <AuthCardShell
      title="Sign in"
      subtitle="Use your email or your institutional account."
      footer={<AuthCardFooter />}
    >
      {/* OAuth Buttons */}
      <div data-animate>
        <OAuthButtons mode="signin" loading={loading} />
      </div>

      {/* Divider */}
      <div data-animate>
        <DividerWithText text="or continue with email" />
      </div>

      {/* Email Form */}
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
              clearFieldError("email");
            }}
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
            value={password}
            onChange={(value) => {
              setPassword(value);
              clearFieldError("password");
            }}
            placeholder="Enter your password"
            error={errors.password}
            autoComplete="current-password"
          />
        </div>

        {/* Forgot Password Link */}
        <div data-animate className="flex justify-end">
          {/* TODO: Wire to /forgot-password when backend supports password reset */}
          <Link
            href="#"
            className="text-sm text-primary hover:underline underline-offset-2"
            onClick={(e) => {
              e.preventDefault();
              // Password reset not implemented yet
            }}
          >
            Forgot password?
          </Link>
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
            className="w-full h-11 rounded-lg bg-primary font-semibold text-white hover:bg-primary/90 transition-all duration-200"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              "Sign in"
            )}
          </Button>
        </div>

        {/* Sign Up Link */}
        <div data-animate className="text-center text-sm text-slate-600">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="font-medium text-primary hover:underline underline-offset-2"
          >
            Create one
          </Link>
        </div>
      </form>
    </AuthCardShell>
  );
}

export default function LoginPage() {
  return (
    <AuthPageLayout>
      <Suspense
        fallback={
          <AuthCardShell title="Sign in" subtitle="Loading...">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          </AuthCardShell>
        }
      >
        <LoginForm />
      </Suspense>
    </AuthPageLayout>
  );
}
