"use client";

import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

export function CTASection() {
  const router = useRouter();

  return (
    <section className="bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50 py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl space-y-8 text-center">
          <h2 className="text-3xl font-bold text-slate-900 sm:text-4xl lg:text-5xl">
            Start practicing by your block today.
          </h2>
          <div className="flex flex-col justify-center gap-4 sm:flex-row">
            <Button
              size="lg"
              onClick={() => router.push("/signup")}
              className="bg-primary shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl"
            >
              Get Started Free
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => router.push("/login")}
              className="border-slate-300"
            >
              Login
            </Button>
          </div>
          <p className="text-sm text-slate-500">No spam. No noise. Just practice.</p>
        </div>
      </div>
    </section>
  );
}
