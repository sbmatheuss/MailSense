import { clsx } from "clsx";

interface BadgeProps {
  label: string;
  variant?: "default" | "success" | "warning" | "danger" | "info";
  size?: "sm" | "md";
}

const VARIANT_CLASS = {
  default: "bg-border text-text-muted",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
  info: "bg-info/10 text-info",
};

export function Badge({ label, variant = "default", size = "sm" }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center font-medium rounded",
        size === "sm" ? "text-xs px-1.5 py-0.5" : "text-sm px-2 py-1",
        VARIANT_CLASS[variant]
      )}
    >
      {label}
    </span>
  );
}
