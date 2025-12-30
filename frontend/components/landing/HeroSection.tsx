"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { CheckCircle2, Clock, BarChart3 } from "lucide-react";
import gsap from "gsap";

export function HeroSection() {
  const router = useRouter();
  const heroRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) return;

    // Hero slide up animation (transform only, no opacity changes)
    // Use fromTo to ensure we control both initial and final states
    if (heroRef.current) {
      const children = Array.from(heroRef.current.children) as HTMLElement[];
      gsap.fromTo(
        children,
        { y: 20, opacity: 1 }, // Initial state: slightly below, fully opaque
        {
          y: 0, // Final state: normal position
          opacity: 1, // Keep fully opaque throughout
          duration: 0.8,
          stagger: 0.1,
          ease: "power3.out",
        },
      );
    }

    // Floating cards animation
    if (cardsRef.current) {
      const cards = cardsRef.current.children;
      gsap.to(cards, {
        y: (i: number) => Math.sin(i) * 10,
        duration: 3 + Math.random() * 2,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
        stagger: 0.3,
      });
    }
  }, []);

  return (
    <section className="relative flex min-h-[90vh] items-center overflow-hidden pb-32 pt-20">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-blue-50/30" />

      {/* Subtle glow effects */}
      <div className="absolute right-20 top-20 h-96 w-96 rounded-full bg-blue-200/20 blur-3xl" />
      <div className="absolute bottom-20 left-20 h-96 w-96 rounded-full bg-teal-200/20 blur-3xl" />

      <div className="container relative z-10 mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Left: Messaging */}
          <div ref={heroRef} className="relative z-10 space-y-6">
            {/* Subtle background panel for better contrast */}
            <div className="absolute -inset-4 -z-10 rounded-lg bg-white/60 opacity-0 backdrop-blur-sm lg:opacity-100" />

            <Badge
              variant="outline"
              className="border-primary bg-white/80 font-medium text-primary"
            >
              Built for MBBS Block System
            </Badge>

            <h1 className="text-4xl font-bold leading-tight text-slate-900 sm:text-5xl lg:text-6xl">
              Practice smarter.
              <br />
              Revise faster.
              <br />
              <span className="text-primary">Walk into exams calm.</span>
            </h1>

            <p className="max-w-xl text-lg font-medium text-slate-700">
              Syllabus-aligned practice tests with explanations, insights, and revision workflows
              designed for real exam conditions.
            </p>

            <div className="flex flex-col gap-4 sm:flex-row">
              <Button
                size="lg"
                onClick={() => router.push("/signup")}
                className="bg-primary font-semibold text-white shadow-lg transition-all hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-xl"
              >
                Get Started Free
              </Button>
            </div>

            {/* Trust micro-strip */}
            <div className="flex flex-wrap gap-6 pt-4 text-sm font-medium text-slate-700">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-accent" />
                <span>Fast. Clean. Exam-grade.</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-accent" />
                <span>Block-based organization</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-accent" />
                <span>Progress insights</span>
              </div>
            </div>
          </div>

          {/* Right: Animated Product Preview Cards */}
          <div ref={cardsRef} className="relative hidden h-[500px] lg:block">
            {/* Card 1: Timed Exam Mode */}
            <Card className="absolute right-0 top-0 w-64 border-t-4 border-primary bg-white p-6 shadow-lg">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  <span className="font-semibold text-slate-900">Timed Exam Mode</span>
                </div>
                <div className="text-3xl font-bold text-slate-900">45:23</div>
                <div className="text-sm text-slate-500">Time remaining</div>
              </div>
            </Card>

            {/* Card 2: Instant Review */}
            <Card className="absolute left-0 top-32 w-64 border-t-4 border-accent bg-white p-6 shadow-lg">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-accent" />
                  <span className="font-semibold text-slate-900">Instant Review</span>
                </div>
                <div className="flex gap-2">
                  <Badge variant="success" className="bg-green-100 text-green-700">
                    Correct
                  </Badge>
                  <Badge variant="destructive" className="bg-red-100 text-red-700">
                    Review
                  </Badge>
                </div>
                <div className="text-sm text-slate-500">25/30 answered</div>
              </div>
            </Card>

            {/* Card 3: Weak Areas Heatmap */}
            <Card className="absolute bottom-0 right-20 w-64 border-t-4 border-primary bg-white p-6 shadow-lg">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" />
                  <span className="font-semibold text-slate-900">Weak Areas</span>
                </div>
                <div className="grid grid-cols-6 gap-1">
                  {Array.from({ length: 18 }).map((_, i) => (
                    <div
                      key={i}
                      className={`h-8 rounded ${
                        i < 6 ? "bg-red-200" : i < 12 ? "bg-yellow-200" : "bg-green-200"
                      }`}
                    />
                  ))}
                </div>
                <div className="text-sm text-slate-500">Block A performance</div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </section>
  );
}
