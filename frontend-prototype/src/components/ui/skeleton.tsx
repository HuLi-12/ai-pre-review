import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-[#1E2A45]/50", className)}
      {...props}
    />
  )
}

export function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-[#0B1020] p-6">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Nav skeleton */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Skeleton className="w-8 h-8 rounded" />
            <Skeleton className="w-40 h-6" />
          </div>
          <Skeleton className="w-24 h-8" />
        </div>

        {/* Metric cards skeleton */}
        <div className="flex gap-4">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="flex-1 h-24 rounded-xl" />
          ))}
        </div>

        {/* Pipeline skeleton */}
        <Skeleton className="h-16 rounded-xl" />

        {/* Main content skeleton */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-3 space-y-2">
            {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-12 rounded-lg" />)}
          </div>
          <div className="col-span-6 space-y-3">
            <Skeleton className="h-24 rounded-xl" />
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-32 rounded-xl" />)}
          </div>
          <div className="col-span-3">
            <Skeleton className="h-48 rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  )
}

export function MetricCardSkeleton() {
  return (
    <div className="glass-card flex-1 min-w-[160px] p-4">
      <Skeleton className="w-16 h-3 mb-3" />
      <Skeleton className="w-20 h-7 mb-1" />
      <Skeleton className="w-24 h-3" />
    </div>
  )
}

export { Skeleton }
