import { useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/uiStore";
import { LogOut } from "lucide-react";

const titles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/inbox": "Inbox",
  "/settings": "Configurações",
};

export default function Header() {
  const { pathname } = useLocation();
  const clearAuth = useAuthStore((s) => s.clearAuth);

  return (
    <header className="h-14 border-b border-border bg-surface flex items-center justify-between px-6 flex-shrink-0">
      <h1 className="text-base font-semibold text-text-primary">{titles[pathname] ?? "MailSense"}</h1>
      <button onClick={clearAuth} className="btn-ghost flex items-center gap-2">
        <LogOut className="w-4 h-4" />
        Sair
      </button>
    </header>
  );
}
