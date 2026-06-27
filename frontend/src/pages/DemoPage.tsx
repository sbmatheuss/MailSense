import { useNavigate } from "react-router-dom";
import { Zap, Mail, BarChart2, Cpu } from "lucide-react";
import { useAuthStore } from "@/stores/uiStore";
import client from "@/api/client";

export default function DemoPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  async function enterDemo() {
    const { data } = await client.post<{ token: string; user_id: number }>("/auth/login/", {
      username: "demo",
      password: "demo123",
    });
    setAuth(data.token, data.user_id);
    navigate("/dashboard");
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8 text-center">
      <div className="flex items-center gap-3 mb-6">
        <Zap className="w-8 h-8 text-primary" />
        <h1 className="text-3xl font-bold text-text-primary">MailSense</h1>
      </div>
      <p className="text-text-secondary text-lg max-w-md mb-10">
        Plataforma de classificação inteligente de e-mails com IA. Classifica, prioriza e sugere respostas automaticamente.
      </p>
      <div className="grid grid-cols-3 gap-6 mb-10 max-w-lg">
        {[
          { icon: Mail, label: "Inbox Inteligente" },
          { icon: Cpu, label: "Classificação com IA" },
          { icon: BarChart2, label: "Dashboard em tempo real" },
        ].map(({ icon: Icon, label }) => (
          <div key={label} className="card flex flex-col items-center gap-2 text-sm text-text-muted">
            <Icon className="w-6 h-6 text-primary" />
            {label}
          </div>
        ))}
      </div>
      <div className="flex gap-3">
        <button onClick={enterDemo} className="btn-primary px-6 py-2.5 text-base">
          Entrar no Demo
        </button>
        <button onClick={() => navigate("/login")} className="btn-ghost px-6 py-2.5 text-base">
          Login
        </button>
      </div>
    </div>
  );
}
