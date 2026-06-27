import { useDashboardOverview, useDashboardByCategory, useDashboardByPriority, useDashboardTrends, useTopSenders } from "@/api/dashboard";
import { Mail, AlertTriangle, Clock, CheckCircle } from "lucide-react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, ResponsiveContainer } from "recharts";

const CATEGORY_COLORS: Record<string, string> = {
  support: "#6366F1", billing: "#F59E0B", bug: "#EF4444", feature: "#22C55E",
  sales: "#3B82F6", internal: "#8B5CF6", newsletter: "#64748B", spam: "#94A3B8", other: "#CBD5E1",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "#EF4444", high: "#F59E0B", medium: "#6366F1", low: "#22C55E",
};

function OverviewCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number | undefined; color: string }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-text-muted text-xs">{label}</p>
        <p className="text-2xl font-bold text-text-primary">{value ?? "—"}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: overview } = useDashboardOverview();
  const { data: byCategory } = useDashboardByCategory();
  const { data: byPriority } = useDashboardByPriority();
  const { data: trends } = useDashboardTrends(30);
  const { data: topSenders } = useTopSenders();

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <OverviewCard icon={Mail} label="Total de E-mails" value={overview?.total} color="bg-primary/10 text-primary" />
        <OverviewCard icon={AlertTriangle} label="Urgentes" value={overview?.urgent} color="bg-danger/10 text-danger" />
        <OverviewCard icon={Clock} label="Pendentes de Ação" value={overview?.pending_action} color="bg-warning/10 text-warning" />
        <OverviewCard icon={CheckCircle} label="Classificados" value={overview?.classified} color="bg-success/10 text-success" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="text-sm font-semibold text-text-primary mb-4">Por Categoria</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={byCategory ?? []} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={80}>
                {(byCategory ?? []).map((entry) => (
                  <Cell key={entry.category} fill={CATEGORY_COLORS[entry.category] ?? "#6366F1"} />
                ))}
              </Pie>
              <Tooltip formatter={(v, n) => [v, n]} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="text-sm font-semibold text-text-primary mb-4">Por Prioridade</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={byPriority ?? []}>
              <XAxis dataKey="priority" tick={{ fill: "#94A3B8", fontSize: 12 }} />
              <YAxis tick={{ fill: "#94A3B8", fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {(byPriority ?? []).map((entry) => (
                  <Cell key={entry.priority} fill={PRIORITY_COLORS[entry.priority] ?? "#6366F1"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-text-primary mb-4">Tendência (30 dias)</h3>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={trends ?? []}>
            <XAxis dataKey="day" tick={{ fill: "#94A3B8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#6366F1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h3 className="text-sm font-semibold text-text-primary mb-4">Top Remetentes</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-text-muted text-left">
              <th className="pb-2 font-medium">Remetente</th>
              <th className="pb-2 font-medium text-right">E-mails</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {(topSenders ?? []).map((s: { from_address: string; from_name: string; count: number }) => (
              <tr key={s.from_address}>
                <td className="py-2 text-text-secondary">{s.from_name || s.from_address}</td>
                <td className="py-2 text-right text-text-primary font-medium">{s.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
