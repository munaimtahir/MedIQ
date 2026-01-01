"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import gsap from "gsap";
import { cn } from "@/lib/utils";

interface AuthPageLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function AuthPageLayout({ children, className }: AuthPageLayoutProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (!containerRef.current) return;

    if (prefersReducedMotion) {
      gsap.set(containerRef.current, { opacity: 1 });
    } else {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.3, ease: "power2.out" }
      );
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className={cn(
        "min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30",
        className
      )}
    >
      {/* Top Bar */}
      <div className="border-b border-slate-200 bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
                <span className="text-sm font-bold text-white">E</span>
              </div>
              <span className="font-semibold text-slate-900">Exam Prep</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content - centered card */}
      <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-12">
        {children}
      </div>

      {/* Footer */}
      <div className="border-t border-slate-200 bg-white/50">
        <div className="container mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex justify-center gap-6 text-sm text-slate-600">
            <Link href="/legal" className="transition-colors hover:text-slate-900">
              Terms
            </Link>
            <span>•</span>
            <Link href="/legal" className="transition-colors hover:text-slate-900">
              Privacy
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
