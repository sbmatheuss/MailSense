import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { useLogin } from "@/api/auth";
import { useAuthStore } from "@/stores/uiStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const login = useLogin();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await login.mutateAsync(form);
      setAuth(data.token, data.user_id);
      navigate("/dashboard");
    } catch {
      setError("Usuário ou senha inválidos.");
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <Zap className="w-6 h-6 text-primary" />
          <span className="text-xl font-bold text-text-primary">MailSense</span>
        </div>
        <div className="card">
          <h2 className="text-lg font-semibold text-text-primary mb-6">Entrar</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-text-secondary mb-1">Usuário</label>
              <input
                type="text"
                value={form.username}
                onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">Senha</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                className="w-full bg-background border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary"
                autoComplete="current-password"
              />
            </div>
            {error && <p className="text-danger text-sm">{error}</p>}
            <button type="submit" disabled={login.isPending} className="btn-primary w-full">
              {login.isPending ? "Entrando..." : "Entrar"}
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-text-muted">
            Demo:{" "}
            <button onClick={() => setForm({ username: "demo", password: "demo123" })} className="text-primary hover:underline">
              usar conta demo
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
