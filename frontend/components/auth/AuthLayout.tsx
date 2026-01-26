"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";

interface AuthLayoutProps {
  children: React.ReactNode;
  rightPanel: React.ReactNode;
}

const container = {
  hidden: { opacity: 1 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export function AuthLayout({ children, rightPanel }: AuthLayoutProps) {

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
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2"
        >
          {/* Left: Auth Card */}
          <motion.div variants={item} className="flex w-full justify-center lg:justify-end">
            <div className="w-full max-w-[420px]">{children}</div>
          </motion.div>

          {/* Right: Value Panel (Desktop only) */}
          <motion.div variants={item} className="hidden lg:block">
            <div className="max-w-md">{rightPanel}</div>
          </motion.div>
        </motion.div>
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
