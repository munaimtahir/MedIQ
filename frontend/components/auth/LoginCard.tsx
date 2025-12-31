"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { authClient, type User } from "@/lib/authClient";
import { notify } from "@/lib/notify";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Eye, EyeOff, Loader2 } from "lucide-react";

export function LoginCard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string; general?: string }>({});

  const validate = () => {
    const newErrors: { email?: string; password?: string } = {};
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
      const result = await authClient.login({ email: email.trim(), password });

      if (result.error) {
        // Handle specific error codes
        if (result.error.code === "RATE_LIMITED") {
          const retryAfter = (result.error.details as { retry_after_seconds?: number })?.retry_after_seconds;
          setErrors({
            general: `Too many login attempts. Please try again in ${retryAfter || "a few"} seconds.`,
          });
        } else if (result.error.code === "ACCOUNT_LOCKED") {
          const lockExpires = (result.error.details as { lock_expires_in?: number })?.lock_expires_in;
          setErrors({
            general: `Account temporarily locked. Please try again in ${lockExpires || "a few"} minutes.`,
          });
        } else {
          setErrors({ general: result.error.message || "Invalid email or password" });
        }
        notify.error("Login failed", result.error.message || "Invalid email or password");
        return;
      }

      if (result.mfa_required) {
        // Handle MFA - redirect to MFA page (to be implemented)
        notify.info("MFA Required", "Please complete multi-factor authentication");
        // TODO: Redirect to MFA page with mfa_token
        return;
      }

      if (result.data?.user) {
        const user = result.data.user as User;
        notify.success("Welcome back", "You're logged in.");

        // Get full user details to check onboarding
        const meResult = await authClient.me();
        if (meResult.data?.user) {
          const fullUser = meResult.data.user as User;
          // Redirect based on onboarding status
          const redirect = searchParams.get("redirect");
          if (redirect) {
            router.push(redirect);
          } else if (!fullUser.onboarding_completed) {
            router.push("/student/onboarding");
          } else {
            // Redirect based on role
            if (user.role === "ADMIN" || user.role === "REVIEWER") {
              router.push("/admin");
            } else {
              router.push("/student/dashboard");
            }
          }
        } else {
          // Fallback redirect
          router.push("/student/dashboard");
        }
      }
    } catch (error: any) {
      setErrors({ general: error.message || "An error occurred. Please try again." });
      notify.error("Login failed", error.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="rounded-xl border-slate-200 shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold text-slate-900">Welcome back</CardTitle>
        <CardDescription className="text-slate-600">
          Log in to continue your practice.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-slate-900">
              Email or phone
            </Label>
            <Input
              id="email"
              type="text"
              placeholder="Enter your email or phone"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (errors.email) setErrors({ ...errors, email: undefined });
              }}
              className={errors.email ? "border-red-500" : ""}
            />
            {errors.email && <p className="text-sm text-red-600">{errors.email}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-slate-900">
              Password
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errors.password) setErrors({ ...errors, password: undefined });
                }}
                className={errors.password ? "border-red-500 pr-10" : "pr-10"}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-700"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && <p className="text-sm text-red-600">{errors.password}</p>}
          </div>

          <div className="flex items-center justify-between">
            <Link href="#" className="text-sm text-primary hover:underline">
              Forgot password?
            </Link>
          </div>

          {errors.general && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">
              {errors.general}
            </div>
          )}

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-primary font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Logging in...
              </>
            ) : (
              "Log in"
            )}
          </Button>
        </form>

        <div className="mt-6">
          <Separator className="my-6" />
          <div className="space-y-3">
            <div className="text-center text-sm text-slate-600">
              New here?{" "}
              <Link href="/signup" className="font-medium text-primary hover:underline">
                Create an account
              </Link>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
