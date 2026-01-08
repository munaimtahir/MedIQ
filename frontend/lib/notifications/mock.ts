/**
 * Mock notifications data for development.
 * Only used when NEXT_PUBLIC_NOTIFICATIONS_MOCK=1
 */

import { NotificationItem } from "./types";

export const mockNotifications: NotificationItem[] = [
  {
    id: "1",
    type: "announcement",
    title: "Welcome to the Medical Exam Prep Platform",
    body: "We're excited to have you here! Start by selecting your academic year and blocks in Settings. You can begin practicing immediately with the blocks you've unlocked.",
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
    read_at: null,
  },
  {
    id: "2",
    type: "system",
    title: "Syllabus Update: New Themes Added",
    body: "We've added new themes to Block A. Check out the updated syllabus to see what's new. These themes are now available for practice.",
    created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
    read_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(), // Read 4 days ago
  },
  {
    id: "3",
    type: "reminder",
    title: "Continue Your Practice",
    body: "You haven't practiced in a while. Keep your skills sharp by completing a practice session today. Even 10 questions can help maintain your knowledge.",
    created_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
    read_at: null,
  },
  {
    id: "4",
    type: "announcement",
    title: "New Practice Modes Available",
    body: "We've added new practice modes including timed exam mode and mixed practice. Try them out in the practice builder to see which works best for you.",
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days ago
    read_at: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(), // Read 6 days ago
  },
];
