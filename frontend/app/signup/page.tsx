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
          setErrors({ email: "An account with this email already exists" });
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
        // Success - route to onboarding (new users always go to onboarding)
        await routeAfterAuth(router.push);
      }
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "An error occurred";
      setErrors({ general: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthPageLayout>
      <AuthCardShell
        title="Create your account"
        subtitle="You'll set your year and blocks in the next step."
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
