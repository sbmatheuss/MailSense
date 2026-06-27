import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import client from "./client";
import type { EmailSummary, EmailDetail, PaginatedResponse } from "@/types";

interface EmailFilters {
  category?: string;
  priority?: string;
  sentiment?: string;
  status?: string;
  requires_action?: boolean;
  date_from?: string;
  date_to?: string;
  search?: string;
  ordering?: string;
  page?: number;
}

export function useEmails(filters: EmailFilters = {}) {
  return useQuery({
    queryKey: ["emails", filters],
    queryFn: () =>
      client.get<PaginatedResponse<EmailSummary>>("/emails/", { params: filters }).then((r) => r.data),
  });
}

export function useEmail(id: number | null) {
  return useQuery({
    queryKey: ["email", id],
    queryFn: () => client.get<EmailDetail>(`/emails/${id}/`).then((r) => r.data),
    enabled: id !== null,
  });
}

export function useArchiveEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.post(`/emails/${id}/archive/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emails"] }),
  });
}

export function useReplyEmail() {
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: string }) =>
      client.post(`/emails/${id}/reply/`, { body }),
  });
}

export function useSyncEmails() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => client.post("/emails/sync/"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emails"] }),
  });
}

export function useCorrectClassification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: { category: string; priority: string; sentiment: string } }) =>
      client.patch(`/emails/${id}/classification/`, data),
    onSuccess: (_data, { id }) => qc.invalidateQueries({ queryKey: ["email", id] }),
  });
}
