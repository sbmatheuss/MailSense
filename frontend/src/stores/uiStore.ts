import { create } from "zustand";
import { persist } from "zustand/middleware";

// --- Auth ---

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

// --- UI ---

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

// --- Toasts ---

export interface Toast {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Toast) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (toast) =>
    set((s) => ({
      toasts: s.toasts.some((t) => t.id === toast.id)
        ? s.toasts
        : [...s.toasts, toast],
    })),
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
