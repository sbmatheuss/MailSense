import { NavLink } from "react-router-dom";
import { LayoutDashboard, Inbox, Settings, Zap } from "lucide-react";
import { clsx } from "clsx";

const nav = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/inbox", icon: Inbox, label: "Inbox" },
  { to: "/settings", icon: Settings, label: "Configurações" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 flex-shrink-0 bg-surface border-r border-border flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-primary" />
          <span className="font-semibold text-text-primary">MailSense</span>
        </div>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2 rounded text-sm transition-colors duration-150",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
              )
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
