import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

export interface EmailFilters {
  category?: string;
  priority?: string;
  sentiment?: string;
  requires_action?: string;
  search?: string;
  ordering?: string;
  page?: string;
}

export function useEmailFilters() {
  const [params, setParams] = useSearchParams();

  const filters: EmailFilters = {
    category: params.get("category") ?? undefined,
    priority: params.get("priority") ?? undefined,
    sentiment: params.get("sentiment") ?? undefined,
    requires_action: params.get("requires_action") ?? undefined,
    search: params.get("search") ?? undefined,
    ordering: params.get("ordering") ?? undefined,
    page: params.get("page") ?? undefined,
  };

  const setFilter = useCallback(
    (key: keyof EmailFilters, value: string | undefined) => {
      setParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        next.delete("page");
        return next;
      });
    },
    [setParams]
  );

  const clearFilters = useCallback(() => setParams({}), [setParams]);

  return { filters, setFilter, clearFilters };
}
