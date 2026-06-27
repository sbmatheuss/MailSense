export function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffH = diffMs / (1000 * 60 * 60);

  if (diffH < 1) return `${Math.round(diffMs / 60000)}min`;
  if (diffH < 24) return `${Math.round(diffH)}h`;
  if (diffH < 48) return "ontem";
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max)}…`;
}

export function formatSender(name: string, address: string): string {
  return name ? name : address.split("@")[0];
}

export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}
