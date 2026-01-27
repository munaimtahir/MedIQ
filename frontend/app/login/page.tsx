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
  const linkEmail = searchParams.get("email");
  const mfaRequired = searchParams.get("mfa");
  const emailParam = searchParams.get("email");

  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showResendVerification, setShowResendVerification] = useState(false);
  const [resending, setResending] = useState(false);
  const [oauthOnlyProvider, setOauthOnlyProvider] = useState<string | null>(null);
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

  // Pre-fill email from query param if present
  useEffect(() => {
    if (emailParam && !email) {
      setEmail(emailParam);
    }
  }, [emailParam, email]);

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
        if (result.error.code === "OAUTH_ONLY_ACCOUNT") {
          const provider = (result.error.details as { provider?: string })?.provider || "OAuth";
          const providerDisplay =
            provider === "GOOGLE" ? "Google" : provider === "MICROSOFT" ? "Microsoft" : provider;
          setOauthOnlyProvider(provider);
          setErrors({
            general: `This account was created with ${providerDisplay}. Please sign in with ${providerDisplay} instead.`,
          });
        } else if (result.error.code === "EMAIL_NOT_VERIFIED") {
          setErrors({
            general: "Please verify your email before logging in.",
          });
          // Show resend verification option
          setShowResendVerification(true);
        } else if (result.error.code === "RATE_LIMITED") {
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

  const handleResendVerification = async () => {
    if (!email.trim()) return;

    setResending(true);
    setErrors({});

    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        setErrors({ general: data.error?.message || "Failed to resend verification email" });
      } else {
        setErrors({});
        setShowResendVerification(false);
        // Show success - you could use a toast here
        setErrors({ general: "Verification email sent! Please check your inbox." });
        setTimeout(() => setErrors({}), 5000);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setErrors({ general: errorMessage });
    } finally {
      setResending(false);
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
      {!oauthOnlyProvider && (
        <div data-animate>
          <DividerWithText text="or continue with email" />
        </div>
      )}

      {/* Email Form */}
      <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
        {/* OAuth-only message */}
        {oauthOnlyProvider && (
          <div data-animate className="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <p className="mb-1 text-sm font-medium text-blue-800">
              Use{" "}
              {oauthOnlyProvider === "GOOGLE"
                ? "Google"
                : oauthOnlyProvider === "MICROSOFT"
                  ? "Microsoft"
                  : oauthOnlyProvider}{" "}
              to sign in
            </p>
            <p className="text-xs text-blue-700">
              This account was created with{" "}
              {oauthOnlyProvider === "GOOGLE"
                ? "Google"
                : oauthOnlyProvider === "MICROSOFT"
                  ? "Microsoft"
                  : oauthOnlyProvider}
              . Please use the button above to sign in.
            </p>
          </div>
        )}
        {/* Email Field */}
        <div data-animate className="space-y-2">
          <Label htmlFor="email" className="font-medium text-slate-700">
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
              // Clear OAuth-only state when email changes
              if (oauthOnlyProvider) {
                setOauthOnlyProvider(null);
              }
            }}
            autoComplete="email"
            disabled={loading || !!oauthOnlyProvider}
            data-testid="login-email-input"
            className={`h-11 rounded-lg border-slate-200 bg-white focus:border-primary focus:ring-primary ${
              errors.email ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
            } ${oauthOnlyProvider ? "cursor-not-allowed opacity-50" : ""}`}
          />
          {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
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
            disabled={!!oauthOnlyProvider}
          />
        </div>

        {/* Forgot Password Link */}
        <div data-animate className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-sm text-primary underline-offset-2 hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        {/* Error Alert */}
        {errors.general && (
          <div data-animate>
            <InlineAlert
              variant={errors.general.includes("sent!") ? "success" : "error"}
              message={errors.general}
              onDismiss={() => {
                setErrors((prev) => ({ ...prev, general: undefined }));
                setShowResendVerification(false);
              }}
            />
          </div>
        )}

        {/* Resend Verification */}
        {showResendVerification && (
          <div data-animate className="space-y-2 rounded-lg border border-blue-200 bg-blue-50 p-3">
            <p className="text-sm text-blue-800">
              Your email hasn't been verified yet. Check your inbox or spam folder.
            </p>
            <Button
              onClick={handleResendVerification}
              disabled={resending}
              variant="outline"
              size="sm"
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
          </div>
        )}

        {/* Submit Button */}
        <div data-animate>
          <Button
            type="submit"
            disabled={loading || !!oauthOnlyProvider}
            className="h-11 w-full rounded-lg bg-primary font-semibold text-white transition-all duration-200 hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="login-submit-button"
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
            className="font-medium text-primary underline-offset-2 hover:underline"
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
