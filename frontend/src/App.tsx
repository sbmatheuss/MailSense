import { useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore, useToastStore } from "@/stores/uiStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { ToastContainer } from "@/components/ui/Toast";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import InboxPage from "@/pages/InboxPage";
import SettingsPage from "@/pages/SettingsPage";
import DemoPage from "@/pages/DemoPage";
import MainLayout from "@/components/layout/MainLayout";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function WebSocketBridge() {
  const addToast = useToastStore((s) => s.addToast);
  const qc = useQueryClient();

  const onMessage = useCallback(
    (msg: { type: string; email_id?: number; subject?: string }) => {
      if (msg.type === "critical_email" && msg.email_id) {
        addToast({
          id: `critical-${msg.email_id}`,
          type: "warning",
          message: `E-mail crítico: ${msg.subject ?? "sem assunto"}`,
        });
        qc.invalidateQueries({ queryKey: ["emails"] });
        qc.invalidateQueries({ queryKey: ["dashboard"] });
      }
    },
    [addToast, qc]
  );

  useWebSocket(onMessage);
  return null;
}

export default function App() {
  const token = useAuthStore((s) => s.token);

  return (
    <BrowserRouter>
      {token && <WebSocketBridge />}
      <ToastContainer />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <MainLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
