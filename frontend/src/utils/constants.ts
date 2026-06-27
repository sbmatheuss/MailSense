import type { Category, Priority, Sentiment } from "@/types";

export const CATEGORY_LABELS: Record<Category, string> = {
  support: "Suporte",
  billing: "Financeiro",
  bug: "Bug Report",
  feature: "Feature Request",
  sales: "Vendas",
  internal: "Interno",
  newsletter: "Newsletter",
  spam: "Spam",
  other: "Outro",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  critical: "Crítico",
  high: "Alto",
  medium: "Médio",
  low: "Baixo",
};

export const SENTIMENT_LABELS: Record<Sentiment, string> = {
  positive: "Positivo",
  neutral: "Neutro",
  negative: "Negativo",
  urgent: "Urgente",
};

export const CATEGORY_COLORS: Record<Category, string> = {
  support: "#6366F1",
  billing: "#F59E0B",
  bug: "#EF4444",
  feature: "#22C55E",
  sales: "#3B82F6",
  internal: "#8B5CF6",
  newsletter: "#64748B",
  spam: "#94A3B8",
  other: "#CBD5E1",
};

export const PRIORITY_COLORS: Record<Priority, string> = {
  critical: "#EF4444",
  high: "#F59E0B",
  medium: "#6366F1",
  low: "#22C55E",
};
