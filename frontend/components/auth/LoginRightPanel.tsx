"use client";

import React from "react";
import { CheckCircle2 } from "lucide-react";

export function LoginRightPanel() {
  return (
    <div className="space-y-6">
      <h3 className="text-2xl font-bold text-slate-900">Structured practice. Calm exams.</h3>
      <ul className="space-y-4">
        <li className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-accent" />
          <span className="text-slate-700">Block-based practice</span>
        </li>
        <li className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-accent" />
          <span className="text-slate-700">Exam-like tests</span>
        </li>
        <li className="flex items-start gap-3">
          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-accent" />
          <span className="text-slate-700">Smart review</span>
        </li>
      </ul>
    </div>
  );
}
