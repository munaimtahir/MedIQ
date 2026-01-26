"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface StepContainerProps {
  children: React.ReactNode;
  stepKey: string | number;
  direction?: "forward" | "backward";
  className?: string;
}

export function StepContainer({
  children,
  stepKey,
  direction = "forward",
  className,
}: StepContainerProps) {
  const isForward = direction === "forward";
  const fromX = isForward ? 40 : -40;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={stepKey}
        initial={{ x: fromX, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: -fromX, opacity: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className={cn("w-full", className)}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
