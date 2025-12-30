import { create } from "zustand";

interface UserState {
  userId: string | null;
  role: "student" | "admin" | null;
  setUser: (userId: string, role: "student" | "admin") => void;
  clearUser: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  userId: typeof window !== "undefined" ? localStorage.getItem("userId") : null,
  role:
    typeof window !== "undefined"
      ? (localStorage.getItem("role") as "student" | "admin" | null)
      : null,
  setUser: (userId: string, role: "student" | "admin") => {
    if (typeof window !== "undefined") {
      localStorage.setItem("userId", userId);
      localStorage.setItem("role", role);
    }
    set({ userId, role });
  },
  clearUser: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("userId");
      localStorage.removeItem("role");
    }
    set({ userId: null, role: null });
  },
}));
