import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { useUIStore } from "@/stores/uiStore";
import { clsx } from "clsx";

export default function MainLayout() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar />
      <div className={clsx("flex flex-col flex-1 min-w-0 transition-all duration-modal", sidebarOpen ? "ml-0" : "ml-0")}>
        <Header />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
