import { useState } from "react";
import { useEmails, useEmail, useArchiveEmail, useReplyEmail } from "@/api/emails";
import { useUIStore } from "@/stores/uiStore";
import { clsx } from "clsx";
import type { Priority, Sentiment, Category } from "@/types";

const PRIORITY_COLOR: Record<Priority, string> = {
  critical: "text-danger",
  high: "text-warning",
  medium: "text-primary",
  low: "text-success",
};

const CATEGORY_LABEL: Record<Category, string> = {
  support: "Suporte", billing: "Financeiro", bug: "Bug", feature: "Feature",
  sales: "Vendas", internal: "Interno", newsletter: "Newsletter", spam: "Spam", other: "Outro",
};

const SENTIMENT_COLOR: Record<Sentiment, string> = {
  positive: "bg-success/10 text-success",
  neutral: "bg-border text-text-muted",
  negative: "bg-danger/10 text-danger",
  urgent: "bg-warning/10 text-warning",
};

export default function InboxPage() {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("");
  const selectedId = useUIStore((s) => s.selectedEmailId);
  const selectEmail = useUIStore((s) => s.selectEmail);

  const { data } = useEmails({ search, priority: priority || undefined });
  const { data: detail } = useEmail(selectedId);
  const archive = useArchiveEmail();
  const reply = useReplyEmail();
  const [replyText, setReplyText] = useState("");

  return (
    <div className="flex h-full gap-4 -m-6 overflow-hidden">
      <div className="w-96 flex-shrink-0 flex flex-col border-r border-border">
        <div className="p-3 border-b border-border space-y-2">
          <input
            type="text"
            placeholder="Buscar..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-primary"
          />
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-text-secondary focus:outline-none focus:border-primary"
          >
            <option value="">Todas as prioridades</option>
            <option value="critical">Crítico</option>
            <option value="high">Alto</option>
            <option value="medium">Médio</option>
            <option value="low">Baixo</option>
          </select>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-border">
          {(data?.results ?? []).map((email) => (
            <button
              key={email.id}
              onClick={() => selectEmail(email.id)}
              className={clsx(
                "w-full text-left p-3 hover:bg-surface-hover transition-colors duration-150",
                selectedId === email.id && "bg-surface-hover"
              )}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-muted truncate">{email.from_name || email.from_address}</span>
                {email.classification && (
                  <span className={clsx("text-xs font-medium", PRIORITY_COLOR[email.classification.priority])}>
                    {email.classification.priority}
                  </span>
                )}
              </div>
              <p className={clsx("text-sm truncate", email.is_read ? "text-text-secondary" : "text-text-primary font-medium")}>
                {email.subject}
              </p>
              {email.classification && (
                <p className="text-xs text-text-muted truncate mt-0.5">{email.classification.summary}</p>
              )}
              {email.classification && (
                <div className="flex items-center gap-1.5 mt-1.5">
                  <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                    {CATEGORY_LABEL[email.classification.category]}
                  </span>
                  <span className={clsx("text-xs px-1.5 py-0.5 rounded", SENTIMENT_COLOR[email.classification.sentiment])}>
                    {email.classification.sentiment}
                  </span>
                </div>
              )}
            </button>
          ))}
          {data?.count === 0 && (
            <div className="p-8 text-center text-text-muted text-sm">Nenhum e-mail encontrado.</div>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {detail ? (
          <div className="max-w-2xl space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">{detail.subject}</h2>
              <p className="text-sm text-text-muted mt-1">
                {detail.from_name ? `${detail.from_name} <${detail.from_address}>` : detail.from_address}
              </p>
            </div>
            {detail.classification && (
              <div className="card space-y-2">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Classificação IA</h3>
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">{CATEGORY_LABEL[detail.classification.category]}</span>
                  <span className={clsx("text-xs px-2 py-1 rounded font-medium", PRIORITY_COLOR[detail.classification.priority])}>
                    {detail.classification.priority}
                  </span>
                  <span className={clsx("text-xs px-2 py-1 rounded", SENTIMENT_COLOR[detail.classification.sentiment])}>
                    {detail.classification.sentiment}
                  </span>
                  <span className="text-xs text-text-muted">{Math.round(detail.classification.confidence_score * 100)}% confiança</span>
                </div>
                <p className="text-sm text-text-secondary">{detail.classification.summary}</p>
                {detail.classification.key_topics.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {detail.classification.key_topics.map((t) => (
                      <span key={t} className="text-xs bg-surface-hover text-text-muted px-1.5 py-0.5 rounded">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="card">
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">Corpo</h3>
              <p className="text-sm text-text-secondary whitespace-pre-wrap">{detail.body_text}</p>
            </div>
            {detail.classification?.suggested_reply && (
              <div className="card space-y-3">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Resposta Sugerida</h3>
                <textarea
                  value={replyText || detail.classification.suggested_reply}
                  onChange={(e) => setReplyText(e.target.value)}
                  rows={5}
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => reply.mutate({ id: detail.id, body: replyText || detail.classification!.suggested_reply })}
                    disabled={reply.isPending}
                    className="btn-primary"
                  >
                    Enviar
                  </button>
                  <button onClick={() => archive.mutate(detail.id)} className="btn-ghost">
                    Arquivar
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-text-muted text-sm">
            Selecione um e-mail para visualizar.
          </div>
        )}
      </div>
    </div>
  );
}
