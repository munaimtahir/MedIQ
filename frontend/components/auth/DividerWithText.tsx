"use client";

import * as React from "react";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

interface DividerWithTextProps {
  text: string;
  className?: string;
}

export function DividerWithText({ text, className }: DividerWithTextProps) {
  return (
    <div className={cn("relative my-6", className)}>
      <div className="absolute inset-0 flex items-center">
        <Separator className="w-full" />
      </div>
      <div className="relative flex justify-center text-xs uppercase">
        <span className="bg-white px-3 text-slate-500">{text}</span>
      </div>
    </div>
  );
}
