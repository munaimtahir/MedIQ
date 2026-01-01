"use client";

import * as React from "react";
import { useEffect, useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { cn } from "@/lib/utils";

interface AuthCardShellProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  footer?: React.ReactNode;
  className?: string;
}

export function AuthCardShell({
  children,
  title,
  subtitle,
  footer,
  className,
}: AuthCardShellProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (cardRef.current) {
      if (prefersReducedMotion) {
        // Simple fade for reduced motion
        gsap.fromTo(
          cardRef.current,
          { opacity: 0 },
          { opacity: 1, duration: 0.3, ease: "power2.out" }
        );
      } else {
        // Full animation
        gsap.fromTo(
          cardRef.current,
          { y: 20, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.35, ease: "power2.out" }
        );

        // Stagger children
        if (contentRef.current) {
          const children = contentRef.current.querySelectorAll(
            "[data-animate]"
          );
          gsap.fromTo(
            children,
            { y: 8, opacity: 0 },
            {
              y: 0,
              opacity: 1,
              duration: 0.3,
              stagger: 0.04,
              ease: "power2.out",
              delay: 0.15,
            }
          );
        }
      }
    }
  }, []);

  return (
    <div
      ref={cardRef}
      className={cn(
        "w-full max-w-[520px] rounded-2xl border border-slate-200 bg-white shadow-lg",
        className
      )}
    >
      {/* Header */}
      <div className="px-8 pt-8 pb-2">
        <h1
          data-animate
          className="text-2xl font-semibold tracking-tight text-slate-900"
        >
          {title}
        </h1>
        {subtitle && (
          <p data-animate className="mt-2 text-sm text-slate-500">
            {subtitle}
          </p>
        )}
      </div>

      {/* Content */}
      <div ref={contentRef} className="px-8 py-6">
        {children}
      </div>

      {/* Footer */}
      {footer && (
        <div
          data-animate
          className="border-t border-slate-100 bg-slate-50/50 px-8 py-4 rounded-b-2xl"
        >
          {footer}
        </div>
      )}
    </div>
  );
}

// Standard auth footer with Terms/Privacy links
export function AuthCardFooter() {
  return (
    <p className="text-center text-xs text-slate-500">
      By signing in, you agree to our{" "}
      <Link
        href="/legal"
        className="text-primary hover:underline underline-offset-2"
      >
        Terms
      </Link>{" "}
      and{" "}
      <Link
        href="/legal"
        className="text-primary hover:underline underline-offset-2"
      >
        Privacy Policy
      </Link>
      .
    </p>
  );
}
