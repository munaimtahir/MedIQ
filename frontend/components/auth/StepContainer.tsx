"use client";

import * as React from "react";
import { useEffect, useRef } from "react";
import gsap from "gsap";
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
  const containerRef = useRef<HTMLDivElement>(null);
  const prevKeyRef = useRef<string | number>(stepKey);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (!containerRef.current) return;

    // Determine animation direction based on step change
    const isForward = direction === "forward";
    const fromX = isForward ? 40 : -40;

    if (prevKeyRef.current !== stepKey) {
      if (prefersReducedMotion) {
        // Simple fade for reduced motion
        gsap.fromTo(
          containerRef.current,
          { opacity: 0 },
          { opacity: 1, duration: 0.25, ease: "power2.out" }
        );
      } else {
        // Full slide animation
        gsap.fromTo(
          containerRef.current,
          { x: fromX, opacity: 0 },
          { x: 0, opacity: 1, duration: 0.3, ease: "power2.out" }
        );
      }
      prevKeyRef.current = stepKey;
    } else {
      // Initial render - simple fade in
      gsap.fromTo(
        containerRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.25, ease: "power2.out" }
      );
    }
  }, [stepKey, direction]);

  return (
    <div ref={containerRef} className={cn("w-full", className)}>
      {children}
    </div>
  );
}
