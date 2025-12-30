"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Quote } from "lucide-react";

const testimonials = [
  {
    quote: "Helped me stop wasting time on random MCQs.",
    author: "Medical Student",
  },
  {
    quote: "Block-based practice finally makes sense.",
    author: "MBBS Year 1",
  },
  {
    quote: "Review mode is honestly the best part.",
    author: "Medical Student",
  },
];

export function SocialProof() {
  return (
    <section className="bg-white py-16">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid gap-6 md:grid-cols-3">
          {testimonials.map((testimonial, idx) => (
            <Card key={idx} className="border-slate-200 transition-colors hover:border-primary/50">
              <CardContent className="p-6">
                <Quote className="mb-4 h-8 w-8 text-primary/30" />
                <p className="mb-4 text-slate-700">{testimonial.quote}</p>
                <p className="text-sm text-slate-500">{testimonial.author}</p>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="mt-8 text-center text-sm text-slate-500">Early access feedback (beta)</p>
      </div>
    </section>
  );
}
