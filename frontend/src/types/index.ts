export type Category = "support" | "billing" | "bug" | "feature" | "sales" | "internal" | "newsletter" | "spam" | "other";
export type Priority = "critical" | "high" | "medium" | "low";
export type Sentiment = "positive" | "neutral" | "negative" | "urgent";
export type EmailStatus = "pending" | "processing" | "classified" | "failed";

export interface EmailClassification {
  category: Category;
  priority: Priority;
  sentiment: Sentiment;
  confidence_score: number;
  summary: string;
  key_topics: string[];
  suggested_reply: string;
  urgency_reason: string;
  requires_action: boolean;
  user_corrected: boolean;
  processed_at: string;
  processing_time_ms: number;
}

export interface EmailSummary {
  id: number;
  gmail_id: string;
  from_address: string;
  from_name: string;
  subject: string;
  received_at: string;
  is_read: boolean;
  has_attachments: boolean;
  status: EmailStatus;
  classification: EmailClassification | null;
}

export interface EmailDetail extends EmailSummary {
  thread_id: string;
  to_address: string[];
  cc_address: string[];
  body_text: string;
  body_html: string;
  raw_headers: Record<string, string>;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DashboardOverview {
  total: number;
  urgent: number;
  pending_action: number;
  classified: number;
}

export interface CategoryCount {
  category: Category;
  count: number;
}

export interface PriorityCount {
  priority: Priority;
  count: number;
}

export interface TrendPoint {
  day: string;
  count: number;
}
