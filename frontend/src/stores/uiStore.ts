import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  userId: number | null;
  setAuth: (token: string, userId: number) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      setAuth: (token, userId) => set({ token, userId }),
      clearAuth: () => set({ token: null, userId: null }),
    }),
    { name: "mailsense-auth" }
  )
);

interface UIState {
  sidebarOpen: boolean;
  selectedEmailId: number | null;
  toggleSidebar: () => void;
  selectEmail: (id: number | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  selectedEmailId: null,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  selectEmail: (id) => set({ selectedEmailId: id }),
}));
