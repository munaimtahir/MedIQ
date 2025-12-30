"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import gsap from "gsap";

interface AuthLayoutProps {
  children: React.ReactNode;
  rightPanel: React.ReactNode;
}

export function AuthLayout({ children, rightPanel }: AuthLayoutProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    if (contentRef.current) {
      const children = Array.from(contentRef.current.children) as HTMLElement[];
      gsap.fromTo(
        children,
        { y: 12, opacity: 1 },
        {
          y: 0,
          opacity: 1,
          duration: 0.6,
          stagger: 0.1,
          ease: "power3.out",
        },
      );
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
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

      {/* Main Content */}
      <div className="container mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div ref={contentRef} className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
          {/* Left: Auth Card */}
          <div className="flex w-full justify-center lg:justify-end">
            <div className="w-full max-w-[420px]">{children}</div>
          </div>

          {/* Right: Value Panel (Desktop only) */}
          <div className="hidden lg:block">
            <div className="max-w-md">{rightPanel}</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-auto border-t border-slate-200 bg-white/50">
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
