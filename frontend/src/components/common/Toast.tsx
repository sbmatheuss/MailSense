import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { clsx } from "clsx";

export interface ToastMessage {
  id: string;
  message: string;
  type?: "success" | "error" | "info";
}

interface ToastProps extends ToastMessage {
  onDismiss: (id: string) => void;
}

const TYPE_CLASS = {
  success: "border-success text-success",
  error: "border-danger text-danger",
  info: "border-primary text-primary",
};

function Toast({ id, message, type = "info", onDismiss }: ToastProps) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(id), 4000);
    return () => clearTimeout(t);
  }, [id, onDismiss]);

  return (
    <div
      className={clsx(
        "flex items-center gap-3 bg-surface border rounded px-4 py-3 shadow-lg text-sm min-w-64",
        TYPE_CLASS[type]
      )}
    >
      <span className="flex-1 text-text-primary">{message}</span>
      <button onClick={() => onDismiss(id)} className="text-text-muted hover:text-text-primary">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function ToastContainer({ toasts, onDismiss }: { toasts: ToastMessage[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed bottom-4 right-4 space-y-2 z-50">
      {toasts.map((t) => (
        <Toast key={t.id} {...t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const add = (message: string, type: ToastMessage["type"] = "info") =>
    setToasts((prev) => [...prev, { id: crypto.randomUUID(), message, type }]);
  const dismiss = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));
  return { toasts, add, dismiss };
}
