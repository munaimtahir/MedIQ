"use client";

import { useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, GraduationCap, Clock, Eye, Bookmark, TrendingUp } from "lucide-react";
import gsap from "gsap";

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

export function FeaturesGrid() {
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            gsap.from(entry.target.children, {
              opacity: 0,
              y: 30,
              duration: 0.6,
              stagger: 0.1,
              ease: "power3.out",
            });
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 },
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => observer.disconnect();
  }, []);

  return (
    <section id="features" ref={sectionRef} className="bg-slate-50 py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-bold text-slate-900 sm:text-4xl">
            Everything you need to excel
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-slate-600">
            Built specifically for medical exam preparation with focus on clarity and effectiveness.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            return (
              <Card
                key={idx}
                className="border-slate-200 bg-white transition-all hover:-translate-y-1 hover:border-primary hover:shadow-lg"
              >
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
            );
          })}
        </div>
      </div>
    </section>
  );
}
