"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowRight, ChevronDown } from "lucide-react";
import { motion } from "framer-motion";

const steps = [
  {
    number: 1,
    title: "Choose block/theme",
    description: "Select your focus area from the syllabus.",
  },
  {
    number: 2,
    title: "Take a test",
    description: "Practice in exam-like conditions.",
  },
  {
    number: 3,
    title: "Review with explanation",
    description: "Understand mistakes and learn.",
  },
  {
    number: 4,
    title: "Improve with revision",
    description: "Targeted practice on weak areas.",
  },
];

const container = {
  hidden: { opacity: 1 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export function HowItWorks() {

  return (
    <section id="how-it-works" className="bg-white py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-bold text-slate-900 sm:text-4xl">How it works</h2>
          <p className="text-lg text-slate-600">
            Simple, focused workflow designed for medical students
          </p>
        </div>

        {/* Desktop: Horizontal layout with arrows between cards */}
        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.1 }}
          className="hidden items-center md:grid md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr] md:gap-x-4 lg:gap-x-6"
        >
          {steps.map((step, idx) => (
            <React.Fragment key={idx}>
              <motion.div variants={item}>
                <Card className="flex h-full min-h-[180px] border-slate-200 bg-white transition-colors hover:border-primary">
                  <CardContent className="flex w-full flex-col justify-between p-6">
                    <div>
                      <Badge className="mb-4 flex h-8 w-8 items-center justify-center rounded-full bg-primary p-0 text-sm font-semibold text-white">
                        {step.number}
                      </Badge>
                      <h3 className="mb-2 text-base font-semibold text-slate-900">{step.title}</h3>
                    </div>
                    <p className="text-sm leading-relaxed text-slate-600">{step.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
              {idx < steps.length - 1 && (
                <div className="flex items-center justify-center px-2">
                  <ArrowRight className="h-5 w-5 flex-shrink-0 text-slate-400" />
                </div>
              )}
            </React.Fragment>
          ))}
        </motion.div>

        {/* Mobile/Tablet: Vertical layout with downward chevrons */}
        <div className="space-y-6 md:hidden">
          {steps.map((step, idx) => (
            <div key={idx}>
              <Card className="border-slate-200 bg-white transition-colors hover:border-primary">
                <CardContent className="p-6">
                  <div className="flex items-start gap-4">
                    <Badge className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary p-0 text-sm font-semibold text-white">
                      {step.number}
                    </Badge>
                    <div className="flex-1">
                      <h3 className="mb-2 font-semibold text-slate-900">{step.title}</h3>
                      <p className="text-sm text-slate-600">{step.description}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              {idx < steps.length - 1 && (
                <div className="flex justify-center py-2">
                  <ChevronDown className="h-5 w-5 text-slate-400" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
