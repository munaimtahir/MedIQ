"use client";

import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2 } from "lucide-react";
import { motion } from "framer-motion";

const points = [
  "Structured syllabus navigation (not random MCQs)",
  "Exam-like test player",
  "Review-first learning workflow",
  "Built to scale into adaptive + analytics (coming soon)",
];

const container = {
  hidden: { opacity: 1 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemLeft = {
  hidden: { opacity: 0, x: -30 },
  show: { opacity: 1, x: 0 },
};

export function WhyDifferent() {

  return (
    <section className="bg-white py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Left: Bullets */}
          <motion.div
            variants={container}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.3 }}
            className="space-y-6"
          >
            <motion.h2
              variants={itemLeft}
              className="text-3xl font-bold text-slate-900 sm:text-4xl"
            >
              Why this feels different
            </motion.h2>
            <div className="space-y-4">
              {points.map((point, idx) => (
                <motion.div
                  key={idx}
                  variants={itemLeft}
                  className="flex items-start gap-3"
                >
                  <CheckCircle2 className="mt-0.5 h-6 w-6 flex-shrink-0 text-accent" />
                  <p className="text-lg text-slate-700">{point}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Right: Animated Data Loop with subtle float using Tailwind */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="flex items-center justify-center"
          >
            <Card className="w-full max-w-md animate-float border-slate-200 bg-slate-50 p-8">
              <CardContent className="space-y-6">
                <div className="space-y-2 text-center">
                  <div className="text-2xl font-bold text-primary">Practice</div>
                  <div className="text-slate-400">↓</div>
                </div>
                <div className="space-y-2 text-center">
                  <div className="text-2xl font-bold text-primary">Attempt Data</div>
                  <div className="text-slate-400">↓</div>
                </div>
                <div className="space-y-2 text-center">
                  <div className="text-2xl font-bold text-accent">Insights</div>
                  <div className="text-slate-400">↓</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">Better Practice</div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
