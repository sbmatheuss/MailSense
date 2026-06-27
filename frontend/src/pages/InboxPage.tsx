import { useState } from "react";
import { ChevronLeft, ChevronRight, AlertCircle, Zap } from "lucide-react";
import { clsx } from "clsx";
import { useEmails, useEmail, useArchiveEmail, useReplyEmail, useCorrectClassification } from "@/api/emails";
import { useUIStore } from "@/stores/uiStore";
import { EmailListSkeleton } from "@/components/ui/Skeleton";
import type { Priority, Sentiment, Category } from "@/types";

const PRIORITY_COLOR: Record<Priority, string> = {
  critical: "text-danger",
  high: "text-warning",
  medium: "text-primary",
  low: "text-success",
};

const PRIORITY_BG: Record<Priority, string> = {
  critical: "bg-danger/10 text-danger",
  high: "bg-warning/10 text-warning",
  medium: "bg-primary/10 text-primary",
  low: "bg-success/10 text-success",
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

const CATEGORY_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Categoria" },
  { value: "support", label: "Suporte" },
  { value: "billing", label: "Financeiro" },
  { value: "bug", label: "Bug" },
  { value: "feature", label: "Feature" },
  { value: "sales", label: "Vendas" },
  { value: "internal", label: "Interno" },
  { value: "newsletter", label: "Newsletter" },
  { value: "spam", label: "Spam" },
  { value: "other", label: "Outro" },
];

const PAGE_SIZE = 20;

export default function InboxPage() {
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [replyText, setReplyText] = useState("");
  const [correcting, setCorrecting] = useState(false);
  const [correction, setCorrection] = useState({ category: "", priority: "", sentiment: "" });

  const selectedId = useUIStore((s) => s.selectedEmailId);
  const selectEmail = useUIStore((s) => s.selectEmail);

  const { data, isLoading } = useEmails({
    search: search || undefined,
    priority: priority || undefined,
    category: category || undefined,
    page,
  });

  const { data: detail } = useEmail(selectedId);
  const archive = useArchiveEmail();
  const reply = useReplyEmail();
  const correct = useCorrectClassification();

  function handleSelect(id: number) {
    selectEmail(id);
    setReplyText("");
    setCorrecting(false);
  }

  function handleFilter(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  function startCorrection() {
    if (!detail?.classification) return;
    setCorrection({
      category: detail.classification.category,
      priority: detail.classification.priority,
      sentiment: detail.classification.sentiment,
    });
    setCorrecting(true);
  }

  function submitCorrection() {
    if (!detail) return;
    correct.mutate(
      { id: detail.id, data: correction },
      { onSuccess: () => setCorrecting(false) }
    );
  }

  const totalPages = data ? Math.ceil(data.count / PAGE_SIZE) : 1;

  return (
    <div className="flex h-full gap-4 -m-6 overflow-hidden">
      {/* List pane */}
      <div className="w-96 flex-shrink-0 flex flex-col border-r border-border">
        {/* Filters */}
        <div className="p-3 border-b border-border space-y-2">
          <input
            type="text"
            placeholder="Buscar e-mails..."
            value={search}
            onChange={handleFilter(setSearch)}
            className="w-full bg-background border border-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-primary"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={priority}
              onChange={handleFilter(setPriority)}
              className="bg-background border border-border rounded px-2 py-1.5 text-sm text-text-secondary focus:outline-none focus:border-primary"
            >
              <option value="">Prioridade</option>
              <option value="critical">Crítico</option>
              <option value="high">Alto</option>
              <option value="medium">Médio</option>
              <option value="low">Baixo</option>
            </select>
            <select
              value={category}
              onChange={handleFilter(setCategory)}
              className="bg-background border border-border rounded px-2 py-1.5 text-sm text-text-secondary focus:outline-none focus:border-primary"
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto divide-y divide-border">
          {isLoading ? (
            <EmailListSkeleton />
          ) : data?.count === 0 ? (
            <div className="p-8 text-center text-text-muted text-sm">
              Nenhum e-mail encontrado.
            </div>
          ) : (
            (data?.results ?? []).map((email) => (
              <button
                key={email.id}
                onClick={() => handleSelect(email.id)}
                className={clsx(
                  "w-full text-left p-3 hover:bg-surface-hover transition-colors duration-150",
                  selectedId === email.id && "bg-surface-hover",
                  email.classification?.priority === "critical" && "border-l-2 border-l-danger"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-text-muted truncate flex-1">
                    {email.from_name || email.from_address}
                  </span>
                  <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                    {email.classification?.requires_action && (
                      <AlertCircle className="w-3 h-3 text-warning" />
                    )}
                    {email.classification && (
                      <span className={clsx("text-xs font-medium", PRIORITY_COLOR[email.classification.priority])}>
                        {email.classification.priority}
                      </span>
                    )}
                  </div>
                </div>
                <p className={clsx(
                  "text-sm truncate",
                  email.is_read ? "text-text-secondary" : "text-text-primary font-medium"
                )}>
                  {email.subject}
                </p>
                {email.classification && (
                  <p className="text-xs text-text-muted truncate mt-0.5">
                    {email.classification.summary}
                  </p>
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
            ))
          )}
        </div>

        {/* Pagination */}
        {data && data.count > PAGE_SIZE && (
          <div className="p-2 border-t border-border flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={!data.previous}
              className="btn-ghost p-1 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-text-muted">
              {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.count)} de {data.count}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={!data.next}
              className="btn-ghost p-1 disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Detail pane */}
      <div className="flex-1 overflow-y-auto p-6">
        {detail ? (
          <div className="max-w-2xl space-y-4">
            {/* Header */}
            <div>
              <div className="flex items-start justify-between gap-4">
                <h2 className="text-lg font-semibold text-text-primary">{detail.subject}</h2>
                {detail.classification?.priority === "critical" && (
                  <span className="flex items-center gap-1 text-xs bg-danger/10 text-danger px-2 py-1 rounded flex-shrink-0 border border-danger/20">
                    <Zap className="w-3 h-3" />
                    CRÍTICO
                  </span>
                )}
              </div>
              <p className="text-sm text-text-secondary mt-1">
                {detail.from_name
                  ? `${detail.from_name} <${detail.from_address}>`
                  : detail.from_address}
              </p>
              <p className="text-xs text-text-muted mt-0.5">
                {new Date(detail.received_at).toLocaleString("pt-BR")}
              </p>
            </div>

            {/* Classification */}
            {detail.classification && (
              <div className="card space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                    Classificação IA
                  </h3>
                  {!correcting && (
                    <button
                      onClick={startCorrection}
                      className="text-xs text-primary hover:underline"
                    >
                      Corrigir
                    </button>
                  )}
                </div>

                {correcting ? (
                  <div className="space-y-2">
                    <div className="grid grid-cols-3 gap-2">
                      <select
                        value={correction.category}
                        onChange={(e) => setCorrection((c) => ({ ...c, category: e.target.value }))}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-primary"
                      >
                        {CATEGORY_OPTIONS.slice(1).map((c) => (
                          <option key={c.value} value={c.value}>{c.label}</option>
                        ))}
                      </select>
                      <select
                        value={correction.priority}
                        onChange={(e) => setCorrection((c) => ({ ...c, priority: e.target.value }))}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-primary"
                      >
                        <option value="critical">Crítico</option>
                        <option value="high">Alto</option>
                        <option value="medium">Médio</option>
                        <option value="low">Baixo</option>
                      </select>
                      <select
                        value={correction.sentiment}
                        onChange={(e) => setCorrection((c) => ({ ...c, sentiment: e.target.value }))}
                        className="bg-background border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-primary"
                      >
                        <option value="positive">Positivo</option>
                        <option value="neutral">Neutro</option>
                        <option value="negative">Negativo</option>
                        <option value="urgent">Urgente</option>
                      </select>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={submitCorrection}
                        disabled={correct.isPending}
                        className="btn-primary text-xs py-1"
                      >
                        Salvar
                      </button>
                      <button
                        onClick={() => setCorrecting(false)}
                        className="btn-ghost text-xs py-1"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap gap-2 items-center">
                      <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
                        {CATEGORY_LABEL[detail.classification.category]}
                      </span>
                      <span className={clsx("text-xs px-2 py-1 rounded font-medium", PRIORITY_BG[detail.classification.priority])}>
                        {detail.classification.priority}
                      </span>
                      <span className={clsx("text-xs px-2 py-1 rounded", SENTIMENT_COLOR[detail.classification.sentiment])}>
                        {detail.classification.sentiment}
                      </span>
                      <span className="text-xs text-text-muted">
                        {Math.round(detail.classification.confidence_score * 100)}% confiança
                      </span>
                      {detail.classification.requires_action && (
                        <span className="text-xs bg-warning/10 text-warning px-2 py-1 rounded flex items-center gap-1 border border-warning/20">
                          <AlertCircle className="w-3 h-3" />
                          Requer ação
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-text-secondary">{detail.classification.summary}</p>

                    {detail.classification.urgency_reason && (
                      <p className="text-xs text-warning bg-warning/5 border border-warning/20 rounded px-3 py-2">
                        {detail.classification.urgency_reason}
                      </p>
                    )}

                    {detail.classification.key_topics.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {detail.classification.key_topics.map((t) => (
                          <span key={t} className="text-xs bg-surface-hover text-text-muted px-1.5 py-0.5 rounded">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}

                    {detail.classification.user_corrected && (
                      <p className="text-xs text-text-muted italic">Corrigido manualmente</p>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Body */}
            <div className="card">
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">
                Corpo
              </h3>
              <p className="text-sm text-text-secondary whitespace-pre-wrap">{detail.body_text}</p>
            </div>

            {/* Reply */}
            {detail.classification?.suggested_reply && (
              <div className="card space-y-3">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide">
                  Resposta Sugerida
                </h3>
                <textarea
                  value={replyText || detail.classification.suggested_reply}
                  onChange={(e) => setReplyText(e.target.value)}
                  rows={5}
                  className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary resize-none"
                />
                <div className="flex gap-2 items-center">
                  <button
                    onClick={() =>
                      reply.mutate({
                        id: detail.id,
                        body: replyText || detail.classification!.suggested_reply,
                      })
                    }
                    disabled={reply.isPending}
                    className="btn-primary"
                  >
                    {reply.isPending ? "Enviando..." : "Enviar"}
                  </button>
                  <button
                    onClick={() => archive.mutate(detail.id)}
                    disabled={archive.isPending}
                    className="btn-ghost"
                  >
                    Arquivar
                  </button>
                  {reply.isSuccess && (
                    <span className="text-xs text-success">Resposta enviada!</span>
                  )}
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
