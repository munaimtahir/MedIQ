import type { NextWebVitalsMetric } from "next/app";

export function reportWebVitals(metric: NextWebVitalsMetric): void {
  if (process.env.NODE_ENV === "development") {
    console.log(metric);
  }
  
  // Log performance metrics
  const { id, name, label, value } = metric;
  
  if (label === "web-vital") {
    console.log(`[Web Vital] ${name}: ${value}`);
  } else if (label === "custom") {
    console.log(`[Custom Metric] ${name}: ${value}`);
  }
  
  // TODO: Add analytics reporting here (e.g., Google Analytics, Vercel Analytics)
  // analytics.track('web-vitals', { name, value });
}
