import { afterEach, describe, expect, it } from "vitest";
import { useAuthStore, useToastStore, useUIStore } from "@/stores/uiStore";

// Reset stores to a clean state before each test
afterEach(() => {
  useAuthStore.setState({ token: null, userId: null });
  useUIStore.setState({ sidebarOpen: true, selectedEmailId: null });
  useToastStore.setState({ toasts: [] });
});

// ── useAuthStore ──────────────────────────────────────────────────────────

describe("useAuthStore", () => {
  it("starts with null token and userId", () => {
    const { token, userId } = useAuthStore.getState();
    expect(token).toBeNull();
    expect(userId).toBeNull();
  });

  it("setAuth stores token and userId", () => {
    useAuthStore.getState().setAuth("abc123", 42);
    const { token, userId } = useAuthStore.getState();
    expect(token).toBe("abc123");
    expect(userId).toBe(42);
  });

  it("clearAuth resets to null", () => {
    useAuthStore.getState().setAuth("abc123", 42);
    useAuthStore.getState().clearAuth();
    const { token, userId } = useAuthStore.getState();
    expect(token).toBeNull();
    expect(userId).toBeNull();
  });
});

// ── useUIStore ────────────────────────────────────────────────────────────

describe("useUIStore", () => {
  it("starts with sidebarOpen=true and no selected email", () => {
    const state = useUIStore.getState();
    expect(state.sidebarOpen).toBe(true);
    expect(state.selectedEmailId).toBeNull();
  });

  it("toggleSidebar flips sidebarOpen", () => {
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(false);
    useUIStore.getState().toggleSidebar();
    expect(useUIStore.getState().sidebarOpen).toBe(true);
  });

  it("selectEmail sets selectedEmailId", () => {
    useUIStore.getState().selectEmail(7);
    expect(useUIStore.getState().selectedEmailId).toBe(7);
  });

  it("selectEmail(null) clears selection", () => {
    useUIStore.getState().selectEmail(7);
    useUIStore.getState().selectEmail(null);
    expect(useUIStore.getState().selectedEmailId).toBeNull();
  });
});

// ── useToastStore ─────────────────────────────────────────────────────────

describe("useToastStore", () => {
  it("starts with empty toasts array", () => {
    expect(useToastStore.getState().toasts).toHaveLength(0);
  });

  it("addToast appends a toast", () => {
    useToastStore.getState().addToast({ id: "t1", type: "info", message: "Hello" });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    expect(useToastStore.getState().toasts[0].message).toBe("Hello");
  });

  it("addToast deduplicates by id", () => {
    useToastStore.getState().addToast({ id: "dup", type: "info", message: "First" });
    useToastStore.getState().addToast({ id: "dup", type: "error", message: "Second" });
    expect(useToastStore.getState().toasts).toHaveLength(1);
    expect(useToastStore.getState().toasts[0].message).toBe("First");
  });

  it("addToast allows different ids", () => {
    useToastStore.getState().addToast({ id: "a", type: "info", message: "A" });
    useToastStore.getState().addToast({ id: "b", type: "success", message: "B" });
    expect(useToastStore.getState().toasts).toHaveLength(2);
  });

  it("removeToast deletes by id", () => {
    useToastStore.getState().addToast({ id: "keep", type: "info", message: "Keep" });
    useToastStore.getState().addToast({ id: "gone", type: "error", message: "Gone" });
    useToastStore.getState().removeToast("gone");
    const { toasts } = useToastStore.getState();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].id).toBe("keep");
  });

  it("removeToast with unknown id is a no-op", () => {
    useToastStore.getState().addToast({ id: "t1", type: "info", message: "Msg" });
    useToastStore.getState().removeToast("nonexistent");
    expect(useToastStore.getState().toasts).toHaveLength(1);
  });

  it("supports all toast types", () => {
    const types = ["info", "success", "warning", "error"] as const;
    types.forEach((type, i) => {
      useToastStore.getState().addToast({ id: `t${i}`, type, message: type });
    });
    expect(useToastStore.getState().toasts).toHaveLength(4);
  });
});
