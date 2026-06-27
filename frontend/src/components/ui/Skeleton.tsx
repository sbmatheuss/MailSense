import { clsx } from "clsx";

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse bg-surface-hover rounded", className)} />;
}

export function EmailListSkeleton() {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="p-3 space-y-2">
          <div className="flex justify-between items-center">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-10" />
          </div>
          <Skeleton className="h-3.5 w-52" />
          <Skeleton className="h-3 w-40" />
          <div className="flex gap-1.5 pt-0.5">
            <Skeleton className="h-4 w-14 rounded" />
            <Skeleton className="h-4 w-12 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card flex items-center gap-4">
            <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-7 w-12" />
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <Skeleton className="h-4 w-24 mb-4" />
          <Skeleton className="h-48 w-full" />
        </div>
        <div className="card">
          <Skeleton className="h-4 w-24 mb-4" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
      <div className="card">
        <Skeleton className="h-4 w-32 mb-4" />
        <Skeleton className="h-40 w-full" />
      </div>
    </div>
  );
}
