import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DashboardEmptyState } from "./DashboardEmptyState";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe("DashboardEmptyState", () => {
  it("should render getting started content", () => {
    render(<DashboardEmptyState />);

    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Welcome! Let's get you started.")).toBeInTheDocument();
    expect(screen.getByText("Getting Started")).toBeInTheDocument();
    expect(screen.getByText("Pick your year and blocks")).toBeInTheDocument();
  });

  it("should have links to onboarding and practice", () => {
    render(<DashboardEmptyState />);

    const onboardingLink = screen.getByRole("link", { name: /Go to Onboarding/i });
    expect(onboardingLink).toHaveAttribute("href", "/onboarding");

    const practiceLink = screen.getByRole("link", { name: /Start 10-Question Practice/i });
    expect(practiceLink).toHaveAttribute("href", "/student/practice/build?preset=tutor&count=10");
  });
});
