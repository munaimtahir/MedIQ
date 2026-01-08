"use client";

import { useState, useEffect } from "react";
import { AccountCard } from "@/components/student/settings/AccountCard";
import { AcademicYearCard } from "@/components/student/settings/AcademicYearCard";
import { PracticePreferencesCard } from "@/components/student/settings/PracticePreferencesCard";
import { NotificationsCard } from "@/components/student/settings/NotificationsCard";
import { DangerZoneCard } from "@/components/student/settings/DangerZoneCard";
import { SettingsSkeleton } from "@/components/student/settings/SettingsSkeleton";
import { useYears, useProfile } from "@/lib/settings/hooks";
import { onboardingAPI } from "@/lib/api";

export default function SettingsPage() {
  // Fetch data
  const { years, loading: yearsLoading, error: yearsError } = useYears();
  const { profile, loading: profileLoading, refetch: refetchProfile } = useProfile();

  // Determine current year
  const currentYearName = profile?.selected_year?.display_name || null;
  const currentYearId = years.find((y) => y.name === currentYearName)?.id || null;

  // Get user info from auth endpoint (if available)
  const [userInfo, setUserInfo] = useState<{
    name?: string;
    email?: string;
    role?: string;
  } | null>(null);
  const [userInfoLoading, setUserInfoLoading] = useState(true);

  useEffect(() => {
    // Try to get user info from /auth/me endpoint
    fetch("/api/auth/me", {
      credentials: "include",
    })
      .then((res) => {
        if (res.ok) {
          return res.json();
        }
        return null;
      })
      .then((data) => {
        if (data?.user) {
          setUserInfo({
            name: data.user.name,
            email: data.user.email,
            role: data.user.role,
          });
        }
      })
      .catch(() => {
        // Fallback: use email from profile if available
        if (profile) {
          setUserInfo({
            email: profile.user_id, // Fallback - would need proper email field
            role: "STUDENT",
          });
        }
      })
      .finally(() => setUserInfoLoading(false));
  }, [profile]);

  const handleYearChange = async (yearId: number) => {
    // Find the year name
    const year = years.find((y) => y.id === yearId);
    if (!year) {
      throw new Error("Year not found");
    }

    // Map syllabus year to academic year by name
    // Get onboarding options to find matching academic year
    try {
      const options = await onboardingAPI.getOptions();
      const academicYear = options.years.find((y) => y.display_name === year.name);
      
      if (!academicYear) {
        throw new Error("Could not find matching academic year");
      }

      // Update profile using onboarding endpoint (it handles year updates)
      await onboardingAPI.submitOnboarding({
        year_id: academicYear.id,
        block_ids: [],
        subject_ids: [],
      });

      // Refetch profile
      await refetchProfile();
    } catch (error) {
      console.error("Failed to update year:", error);
      throw error;
    }
  };


  const loading = yearsLoading || profileLoading || userInfoLoading;

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto">
        <SettingsSkeleton />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your curriculum and practice preferences
        </p>
      </div>

      {/* Section 1: Account */}
      <AccountCard
        name={userInfo?.name}
        email={userInfo?.email}
        role={userInfo?.role}
        createdAt={profile?.created_at}
        loading={userInfoLoading}
      />

      {/* Section 2: Academic Context */}
      <AcademicYearCard
        years={years}
        currentYearId={currentYearId}
        loading={yearsLoading}
        error={yearsError}
        onYearChange={handleYearChange}
      />

      {/* Section 3: Practice Preferences */}
      <PracticePreferencesCard />

      {/* Section 4: Notifications */}
      <NotificationsCard />

      {/* Section 5: Danger Zone */}
      <DangerZoneCard />
    </div>
  );
}
