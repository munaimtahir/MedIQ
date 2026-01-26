import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({
  subsets: ["latin"],
  display: "swap", // Prevent invisible text (FOIT)
  preload: true, // Preload critical font
  variable: "--font-inter", // CSS variable for better control
  fallback: ["system-ui", "arial"], // System fallback
});

export const metadata: Metadata = {
  title: {
    default: "Medical Exam Platform - MBBS Exam Preparation",
    template: "%s | Medical Exam Platform",
  },
  description:
    "Comprehensive MBBS exam preparation platform with adaptive learning, spaced repetition, and detailed analytics.",
  keywords: ["MBBS", "medical exams", "exam preparation", "MCQ practice", "Pakistan"],
  openGraph: {
    title: "Medical Exam Platform",
    description: "Comprehensive MBBS exam preparation platform",
    siteName: "Medical Exam Platform",
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Medical Exam Platform",
    description: "Comprehensive MBBS exam preparation",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: "#1E3A8A",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="manifest" href="/manifest.json" />
      </head>
      <body className={inter.className}>
        {children}
        <Toaster />
      </body>
    </html>
  );
}
