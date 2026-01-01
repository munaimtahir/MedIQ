"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

// Get API URL from environment
// Remove /v1 suffix if present since OAuth endpoints include it in the path
const API_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/v1\/?$/, "");

interface OAuthButtonsProps {
  mode: "signin" | "signup";
  loading?: boolean;
  disabled?: boolean;
  className?: string;
}

export function OAuthButtons({
  mode,
  loading,
  disabled,
  className,
}: OAuthButtonsProps) {
  const [loadingProvider, setLoadingProvider] = React.useState<string | null>(null);

  const handleOAuthClick = (provider: "google" | "microsoft") => {
    if (loading || disabled) return;
    
    setLoadingProvider(provider);
    
    // Redirect to backend OAuth start endpoint
    const startUrl = `${API_URL}/v1/auth/oauth/${provider}/start`;
    window.location.assign(startUrl);
  };

  const actionText = mode === "signin" ? "Continue with" : "Sign up with";

  return (
    <div className={cn("space-y-3", className)}>
      {/* Google OAuth */}
      <Button
        type="button"
        variant="outline"
        className={cn(
          "w-full h-11 rounded-lg border-slate-200 bg-white hover:bg-slate-50",
          "text-slate-700 hover:text-slate-700 font-medium transition-all duration-200",
          "shadow-sm hover:shadow"
        )}
        disabled={loading || disabled}
        onClick={() => handleOAuthClick("google")}
      >
        {loadingProvider === "google" ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <GoogleIcon className="mr-2 h-4 w-4" />
        )}
        {actionText} Google
      </Button>

      {/* Microsoft OAuth */}
      <Button
        type="button"
        variant="outline"
        className={cn(
          "w-full h-11 rounded-lg border-slate-200 bg-white hover:bg-slate-50",
          "text-slate-700 hover:text-slate-700 font-medium transition-all duration-200",
          "shadow-sm hover:shadow"
        )}
        disabled={loading || disabled}
        onClick={() => handleOAuthClick("microsoft")}
      >
        {loadingProvider === "microsoft" ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <MicrosoftIcon className="mr-2 h-4 w-4" />
        )}
        {actionText} Microsoft
      </Button>
    </div>
  );
}

// Google Icon
function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

// Microsoft Icon
function MicrosoftIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 23 23">
      <path fill="#f35325" d="M1 1h10v10H1z" />
      <path fill="#81bc06" d="M12 1h10v10H12z" />
      <path fill="#05a6f0" d="M1 12h10v10H1z" />
      <path fill="#ffba08" d="M12 12h10v10H12z" />
    </svg>
  );
}
