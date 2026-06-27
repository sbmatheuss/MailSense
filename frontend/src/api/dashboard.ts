import { useQuery } from "@tanstack/react-query";
import client from "./client";
import type { DashboardOverview, CategoryCount, PriorityCount, TrendPoint } from "@/types";

export function useDashboardOverview() {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => client.get<DashboardOverview>("/dashboard/overview/").then((r) => r.data),
    staleTime: 1000 * 60 * 5,
  });
}

export function useDashboardByCategory() {
  return useQuery({
    queryKey: ["dashboard", "by-category"],
    queryFn: () => client.get<CategoryCount[]>("/dashboard/by-category/").then((r) => r.data),
    staleTime: 1000 * 60 * 5,
  });
}

export function useDashboardByPriority() {
  return useQuery({
    queryKey: ["dashboard", "by-priority"],
    queryFn: () => client.get<PriorityCount[]>("/dashboard/by-priority/").then((r) => r.data),
    staleTime: 1000 * 60 * 5,
  });
}

export function useDashboardTrends(days = 30) {
  return useQuery({
    queryKey: ["dashboard", "trends", days],
    queryFn: () => client.get<TrendPoint[]>("/dashboard/trends/", { params: { days } }).then((r) => r.data),
    staleTime: 1000 * 60 * 5,
  });
}

export function useTopSenders() {
  return useQuery({
    queryKey: ["dashboard", "top-senders"],
    queryFn: () => client.get("/dashboard/top-senders/").then((r) => r.data),
    staleTime: 1000 * 60 * 5,
  });
}
