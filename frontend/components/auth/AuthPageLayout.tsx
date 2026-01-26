"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface AuthPageLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export function AuthPageLayout({ children, className }: AuthPageLayoutProps) {

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30",
        className,
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
    </motion.div>
  );
}
