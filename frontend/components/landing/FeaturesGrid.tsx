"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, GraduationCap, Clock, Eye, Bookmark, TrendingUp } from "lucide-react";
import { motion } from "framer-motion";

const features = [
  {
    icon: BookOpen,
    title: "Block-based practice",
    description: "Block-wise structure, themes, and targeted tests.",
  },
  {
    icon: GraduationCap,
    title: "Tutor mode",
    description: "Learn with feedback and explanations.",
  },
  {
    icon: Clock,
    title: "Exam mode",
    description: "Timed, clean, distraction-free.",
  },
  {
    icon: Eye,
    title: "Smart review",
    description: "See exactly what you got wrong and why.",
  },
  {
    icon: Bookmark,
    title: "Bookmarks",
    description: "Save high-yield questions instantly.",
  },
  {
    icon: TrendingUp,
    title: "Progress insights",
    description: "Trends, weak areas, and practice history.",
  },
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

const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0 },
};

export function FeaturesGrid() {

  return (
    <section id="features" className="bg-slate-50 py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-bold text-slate-900 sm:text-4xl">
            Everything you need to excel
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-slate-600">
            Built specifically for medical exam preparation with focus on clarity and effectiveness.
          </p>
        </div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.1 }}
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <motion.div key={idx} variants={item}>
                <Card className="h-full border-slate-200 bg-white transition-all hover:-translate-y-1 hover:border-primary hover:shadow-lg">
                  <CardHeader>
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-slate-600">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
