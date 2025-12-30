"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useUserStore } from "@/store/userStore";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Eye, EyeOff } from "lucide-react";

// Demo credentials for testing
const DEMO_CREDENTIALS = {
  student: {
    email: "student@demo.com",
    password: "demo123",
    userId: "student-1",
    role: "student" as const,
  },
  admin: {
    email: "admin@demo.com",
    password: "demo123",
    userId: "admin-1",
    role: "admin" as const,
  },
};

export function LoginCard() {
  const router = useRouter();
  const setUser = useUserStore((state) => state.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});

  const validate = () => {
    const newErrors: { email?: string; password?: string } = {};
    if (!email.trim()) {
      newErrors.email = "Email or phone is required";
    }
    if (!password) {
      newErrors.password = "Password is required";
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      // Check for demo credentials
      const normalizedEmail = email.trim().toLowerCase();

      if (
        normalizedEmail === DEMO_CREDENTIALS.student.email &&
        password === DEMO_CREDENTIALS.student.password
      ) {
        setUser(DEMO_CREDENTIALS.student.userId, DEMO_CREDENTIALS.student.role);
        router.push("/student/dashboard");
        return;
      }

      if (
        normalizedEmail === DEMO_CREDENTIALS.admin.email &&
        password === DEMO_CREDENTIALS.admin.password
      ) {
        setUser(DEMO_CREDENTIALS.admin.userId, DEMO_CREDENTIALS.admin.role);
        router.push("/admin");
        return;
      }

      // TODO: Backend integration for real authentication
      setErrors({ email: "Invalid email or password" });
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

          <Button
            type="submit"
            className="w-full bg-primary font-semibold text-white hover:bg-primary/90"
          >
            Log in
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
            <div className="border-t border-slate-200 pt-2 text-center">
              <p className="mb-2 text-xs font-semibold text-slate-500">Demo Test Credentials:</p>
              <div className="space-y-1 text-xs text-slate-600">
                <p>
                  <strong>Student:</strong> student@demo.com / demo123
                </p>
                <p>
                  <strong>Admin:</strong> admin@demo.com / demo123
                </p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
