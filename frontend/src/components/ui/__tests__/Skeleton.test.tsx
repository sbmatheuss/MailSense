import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DashboardSkeleton, EmailListSkeleton, Skeleton } from "../Skeleton";

describe("Skeleton", () => {
  it("renders a div with animate-pulse class", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass("animate-pulse");
  });

  it("applies additional className via prop", () => {
    const { container } = render(<Skeleton className="h-4 w-20" />);
    const el = container.firstChild as HTMLElement;
    expect(el).toHaveClass("h-4");
    expect(el).toHaveClass("w-20");
    expect(el).toHaveClass("animate-pulse");
  });

  it("renders without className prop", () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toBeTruthy();
  });
});

describe("EmailListSkeleton", () => {
  it("renders exactly 6 skeleton rows", () => {
    const { container } = render(<EmailListSkeleton />);
    // Each row is a div.p-3.space-y-2 inside the wrapper
    const rows = container.querySelectorAll(".p-3.space-y-2");
    expect(rows).toHaveLength(6);
  });

  it("renders Skeleton elements inside each row", () => {
    const { container } = render(<EmailListSkeleton />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(6);
  });
});

describe("DashboardSkeleton", () => {
  it("renders 4 overview card skeletons", () => {
    const { container } = render(<DashboardSkeleton />);
    // Four overview cards, each with 'card' class
    const cards = container.querySelectorAll(".card");
    expect(cards.length).toBeGreaterThanOrEqual(4);
  });

  it("renders Skeleton elements", () => {
    const { container } = render(<DashboardSkeleton />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
