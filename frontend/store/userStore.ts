import { create } from "zustand";
import { authClient, type User } from "@/lib/authClient";

interface UserState {
  user: User | null;
  loading: boolean;
  setUser: (user: User) => void;
  clearUser: () => void;
  fetchUser: () => Promise<void>;
}

export const useUserStore = create<UserState>((set, get) => ({
  user: null,
  loading: false,
  setUser: (user: User) => {
    set({ user });
  },
  clearUser: () => {
    set({ user: null });
  },
  fetchUser: async () => {
    if (get().loading) return;
    set({ loading: true });
    try {
      const result = await authClient.me();
      if (result.data?.user) {
        set({ user: result.data.user });
      } else if (result.error) {
        set({ user: null });
      }
    } catch {
      set({ user: null });
    } finally {
      set({ loading: false });
    }
  },
}));

// Selectors to prevent unnecessary re-renders
export const selectUser = (state: UserState) => state.user;
export const selectLoading = (state: UserState) => state.loading;
export const selectFetchUser = (state: UserState) => state.fetchUser;
export const selectSetUser = (state: UserState) => state.setUser;
export const selectClearUser = (state: UserState) => state.clearUser;
