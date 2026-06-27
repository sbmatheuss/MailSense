import { useProfile } from "@/api/auth";
import client from "@/api/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, XCircle } from "lucide-react";

export default function SettingsPage() {
  const { data: profile } = useProfile();
  const qc = useQueryClient();

  const disconnect = useMutation({
    mutationFn: () => client.post("/auth/gmail/disconnect/"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });

  const connect = useMutation({
    mutationFn: () => client.post<{ auth_url: string }>("/auth/gmail/connect/").then((r) => r.data),
    onSuccess: (data) => {
      window.location.href = data.auth_url;
    },
  });

  const seedDemo = useMutation({
    mutationFn: () => client.post("/demo/seed/"),
  });

  const resetDemo = useMutation({
    mutationFn: () => client.post("/demo/reset/"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["emails"] }),
  });

  return (
    <div className="max-w-lg space-y-6">
      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-text-primary">Gmail</h2>
        <div className="flex items-center gap-2">
          {profile?.is_gmail_connected ? (
            <>
              <CheckCircle className="w-4 h-4 text-success" />
              <span className="text-sm text-text-secondary">Conectado</span>
              {profile.last_sync_at && (
                <span className="text-xs text-text-muted ml-2">
                  Última sync: {new Date(profile.last_sync_at).toLocaleString("pt-BR")}
                </span>
              )}
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4 text-danger" />
              <span className="text-sm text-text-secondary">Desconectado</span>
            </>
          )}
        </div>
        <div className="flex gap-2">
          {profile?.is_gmail_connected ? (
            <button onClick={() => disconnect.mutate()} disabled={disconnect.isPending} className="btn-ghost">
              Desconectar Gmail
            </button>
          ) : (
            <button onClick={() => connect.mutate()} disabled={connect.isPending} className="btn-primary">
              Conectar Gmail
            </button>
          )}
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-text-primary">Modo Demo</h2>
        <p className="text-sm text-text-muted">Popula a inbox com 150 e-mails fictícios para demonstração.</p>
        <div className="flex gap-2">
          <button onClick={() => seedDemo.mutate()} disabled={seedDemo.isPending} className="btn-primary">
            {seedDemo.isPending ? "Gerando..." : "Gerar dados demo"}
          </button>
          <button onClick={() => resetDemo.mutate()} disabled={resetDemo.isPending} className="btn-ghost">
            Limpar dados
          </button>
        </div>
        {seedDemo.isSuccess && <p className="text-sm text-success">Dados demo gerados com sucesso!</p>}
      </div>
    </div>
  );
}
