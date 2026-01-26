"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface AuthCardShellProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  footer?: React.ReactNode;
  className?: string;
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.35,
      ease: "easeOut",
      staggerChildren: 0.04,
      delayChildren: 0.15,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
};

export function AuthCardShell({
  children,
  title,
  subtitle,
  footer,
  className,
}: AuthCardShellProps) {

  return (
    <motion.div
      variants={cardVariants}
      initial="hidden"
      animate="show"
      className={cn(
        "w-full max-w-[520px] rounded-2xl border border-slate-200 bg-white shadow-lg",
        className,
      )}
    >
      {/* Header */}
      <div className="px-8 pb-2 pt-8">
        <motion.h1
          variants={itemVariants}
          className="text-2xl font-semibold tracking-tight text-slate-900"
        >
          {title}
        </motion.h1>
        {subtitle && (
          <motion.p variants={itemVariants} className="mt-2 text-sm text-slate-500">
            {subtitle}
          </motion.p>
        )}
      </div>

      {/* Content */}
      <div className="px-8 py-6">{children}</div>

      {/* Footer */}
      {footer && (
        <motion.div
          variants={itemVariants}
          className="rounded-b-2xl border-t border-slate-100 bg-slate-50/50 px-8 py-4"
        >
          {footer}
        </motion.div>
      )}
    </motion.div>
  );
}

// Standard auth footer with Terms/Privacy links
export function AuthCardFooter() {
  return (
    <p className="text-center text-xs text-slate-500">
      By signing in, you agree to our{" "}
      <Link href="/legal" className="text-primary underline-offset-2 hover:underline">
        Terms
      </Link>{" "}
      and{" "}
      <Link href="/legal" className="text-primary underline-offset-2 hover:underline">
        Privacy Policy
      </Link>
      .
    </p>
  );
}
