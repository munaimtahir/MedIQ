/**
 * Client-side wrapper for landing page sections
 */
import { Navbar } from "@/components/landing/Navbar";
import { HeroSection } from "@/components/landing/HeroSection";
import { SocialProof } from "@/components/landing/SocialProof";
import { FeaturesGrid } from "@/components/landing/FeaturesGrid";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { BlocksSection } from "@/components/landing/BlocksSection";
import { WhyDifferent } from "@/components/landing/WhyDifferent";
import { PricingSection } from "@/components/landing/PricingSection";
import { CTASection } from "@/components/landing/CTASection";
import { Footer } from "@/components/landing/Footer";

export function LandingClient() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <main>
        <HeroSection />
        <SocialProof />
        <FeaturesGrid />
        <HowItWorks />
        <BlocksSection />
        <WhyDifferent />
        <PricingSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
