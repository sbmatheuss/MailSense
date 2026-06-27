import { useEffect } from "react";
import { X, AlertTriangle, CheckCircle, Info, XCircle } from "lucide-react";
import { clsx } from "clsx";
import { useToastStore, type Toast } from "@/stores/uiStore";

const ICONS = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
};

const BORDER_COLORS = {
  info: "border-info",
  success: "border-success",
  warning: "border-warning",
  error: "border-danger",
};

const ICON_COLORS = {
  info: "text-info",
  success: "text-success",
  warning: "text-warning",
  error: "text-danger",
};

const AUTO_DISMISS_MS = 5_000;

function ToastItem({ toast }: { toast: Toast }) {
  const removeToast = useToastStore((s) => s.removeToast);
  const Icon = ICONS[toast.type];

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), AUTO_DISMISS_MS);
    return () => clearTimeout(timer);
  }, [toast.id, removeToast]);

  return (
    <div
      className={clsx(
        "flex items-start gap-3 bg-surface border rounded-lg p-3 shadow-lg w-80 text-sm",
        BORDER_COLORS[toast.type]
      )}
    >
      <Icon className={clsx("w-4 h-4 mt-0.5 flex-shrink-0", ICON_COLORS[toast.type])} />
      <p className="flex-1 text-text-primary">{toast.message}</p>
      <button
        onClick={() => removeToast(toast.id)}
        className="text-text-muted hover:text-text-primary flex-shrink-0 transition-colors"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <div className="pointer-events-auto flex flex-col gap-2">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </div>
    </div>
  );
}
