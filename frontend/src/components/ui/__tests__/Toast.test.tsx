import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastContainer } from "../Toast";
import { useToastStore } from "@/stores/uiStore";

beforeEach(() => {
  useToastStore.setState({ toasts: [] });
});

function addToast(opts: { id?: string; type?: "info" | "success" | "warning" | "error"; message?: string } = {}) {
  // Direct synchronous Zustand update — no act() needed before render
  useToastStore.getState().addToast({
    id: opts.id ?? "toast-1",
    type: opts.type ?? "info",
    message: opts.message ?? "Test message",
  });
}

describe("ToastContainer", () => {
  it("renders nothing when there are no toasts", () => {
    const { container } = render(<ToastContainer />);
    expect(container.firstChild).toBeNull();
  });

  it("renders toast message when a toast is added before render", () => {
    addToast({ message: "Something happened" });
    render(<ToastContainer />);
    expect(screen.getByText("Something happened")).toBeInTheDocument();
  });

  it("renders multiple distinct toasts", () => {
    useToastStore.getState().addToast({ id: "a", type: "info", message: "First" });
    useToastStore.getState().addToast({ id: "b", type: "error", message: "Second" });
    render(<ToastContainer />);
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("removes toast when close button is clicked", async () => {
    // Real timers — userEvent needs them to function correctly
    addToast({ message: "Click to close me" });
    render(<ToastContainer />);
    expect(screen.getByText("Click to close me")).toBeInTheDocument();

    const user = userEvent.setup({ delay: null });
    await user.click(screen.getByRole("button"));

    expect(screen.queryByText("Click to close me")).not.toBeInTheDocument();
  });

  it("renders info toast with border-info class", () => {
    addToast({ type: "info", message: "Info toast" });
    const { container } = render(<ToastContainer />);
    expect(container.querySelector(".border-info")).toBeInTheDocument();
  });

  it("renders error toast with border-danger class", () => {
    addToast({ type: "error", message: "Error toast" });
    const { container } = render(<ToastContainer />);
    expect(container.querySelector(".border-danger")).toBeInTheDocument();
  });

  it("renders success toast with border-success class", () => {
    addToast({ type: "success", message: "Success toast" });
    const { container } = render(<ToastContainer />);
    expect(container.querySelector(".border-success")).toBeInTheDocument();
  });

  describe("auto-dismiss (fake timers)", () => {
    beforeEach(() => { vi.useFakeTimers(); });
    afterEach(() => { act(() => { vi.runAllTimers(); }); vi.useRealTimers(); });

    it("auto-dismisses toast after 5 seconds", () => {
      addToast({ message: "Auto-dismiss me" });
      render(<ToastContainer />);
      expect(screen.getByText("Auto-dismiss me")).toBeInTheDocument();

      act(() => { vi.advanceTimersByTime(5000); });

      expect(screen.queryByText("Auto-dismiss me")).not.toBeInTheDocument();
    });

    it("does not auto-dismiss before 5 seconds", () => {
      addToast({ message: "Still visible" });
      render(<ToastContainer />);

      act(() => { vi.advanceTimersByTime(4999); });

      expect(screen.getByText("Still visible")).toBeInTheDocument();
    });
  });
});
