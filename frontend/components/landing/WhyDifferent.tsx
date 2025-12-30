"use client";

import { useEffect, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle2 } from "lucide-react";
import gsap from "gsap";

const points = [
  "Structured syllabus navigation (not random MCQs)",
  "Exam-like test player",
  "Review-first learning workflow",
  "Built to scale into adaptive + analytics (coming soon)",
];

export function WhyDifferent() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const visualRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            if (entry.target === sectionRef.current) {
              if (!prefersReducedMotion) {
                gsap.from(entry.target.children, {
                  opacity: 0,
                  x: -30,
                  duration: 0.6,
                  stagger: 0.1,
                  ease: "power3.out",
                });
              }
            }
            if (entry.target === visualRef.current) {
              if (!prefersReducedMotion) {
                // Subtle entrance animation: fade in + slight slide up
                gsap.from(visualRef.current, {
                  opacity: 0,
                  y: 20,
                  duration: 0.8,
                  ease: "power3.out",
                });

                // Very subtle idle animation: gentle y-drift (no rotation)
                gsap.to(visualRef.current, {
                  y: -6,
                  duration: 6,
                  repeat: -1,
                  yoyo: true,
                  ease: "sine.inOut",
                });
              }
            }
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 },
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    if (visualRef.current) observer.observe(visualRef.current);

    return () => observer.disconnect();
  }, []);

  return (
    <section className="bg-white py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Left: Bullets */}
          <div ref={sectionRef} className="space-y-6">
            <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl">
              Why this feels different
            </h2>
            <div className="space-y-4">
              {points.map((point, idx) => (
                <div key={idx} className="flex items-start gap-3">
                  <CheckCircle2 className="mt-0.5 h-6 w-6 flex-shrink-0 text-accent" />
                  <p className="text-lg text-slate-700">{point}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Animated Data Loop */}
          <div ref={visualRef} className="flex items-center justify-center">
            <Card className="w-full max-w-md border-slate-200 bg-slate-50 p-8">
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
          </div>
        </div>
      </div>
    </section>
  );
}
