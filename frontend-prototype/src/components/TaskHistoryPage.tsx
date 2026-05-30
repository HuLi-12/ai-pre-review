import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table"
import { Shield, Search, Clock, CheckCheck, XCircle, ChevronLeft, ChevronRight } from "lucide-react"

interface TaskItem {
  id: number
  pr_url: string
  status: string
  risk_level: string
  created_at: string
  summary: string | null
}

const mockTasks: TaskItem[] = [
  { id: 142, pr_url: "https://github.com/org/repo/pull/142", status: "DONE", risk_level: "HIGH", created_at: "2026-05-30 10:30", summary: "feat: order batch processing pipeline" },
  { id: 141, pr_url: "https://github.com/org/repo/pull/141", status: "DONE", risk_level: "LOW", created_at: "2026-05-29 14:20", summary: "chore: update README" },
  { id: 140, pr_url: "https://github.com/org/repo/pull/140", status: "DONE", risk_level: "MEDIUM", created_at: "2026-05-28 09:15", summary: "fix: user login validation" },
  { id: 139, pr_url: "https://github.com/org/repo/pull/139", status: "FAILED", risk_level: "-", created_at: "2026-05-27 16:45", summary: "feat: payment integration" },
  { id: 138, pr_url: "https://github.com/org/repo/pull/138", status: "DONE", risk_level: "CRITICAL", created_at: "2026-05-26 11:00", summary: "refactor: database migration" },
  { id: 137, pr_url: "https://github.com/org/repo/pull/137", status: "PENDING", risk_level: "-", created_at: "2026-05-25 08:30", summary: "feat: add caching layer" },
]

const statusConfig: Record<string, { color: string; icon: React.ElementType; label: string }> = {
  DONE: { color: "text-emerald-400", icon: CheckCheck, label: "Done" },
  FAILED: { color: "text-red-400", icon: XCircle, label: "Failed" },
  PENDING: { color: "text-amber-400", icon: Clock, label: "Pending" },
}

const riskBadge: Record<string, string> = {
  CRITICAL: "bg-red-500/10 text-red-400 border-red-500/20",
  HIGH: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  MEDIUM: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  LOW: "bg-gray-500/10 text-gray-400 border-gray-500/20",
}

function Navbar({ onNavigate }: { onNavigate: (page: string) => void }) {
  return (
    <nav className="glass-nav border-b border-[#1E2A45] px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-[#38BDF8]" />
          <span className="text-lg font-bold">
            <span className="text-[#38BDF8]">AI</span>{" "}
            <span className="text-[#E2E8F0]">Review Cockpit</span>
          </span>
        </div>
        <div className="flex items-center gap-4 text-sm text-[#64748B]">
          <span className="hover:text-[#E2E8F0] cursor-pointer transition" onClick={() => onNavigate("home")}>Home</span>
          <span className="text-[#E2E8F0] cursor-pointer transition">History</span>
          <span className="hover:text-[#E2E8F0] cursor-pointer transition" onClick={() => onNavigate("rules")}>Rules</span>
        </div>
      </div>
    </nav>
  )
}

export default function TaskHistoryPage({ onNavigate, onViewReport }: { onNavigate: (page: string) => void; onViewReport: (taskId: number) => void }) {
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [page, setPage] = useState(1)
  const perPage = 5

  const filtered = mockTasks.filter((t) => {
    const matchSearch = !search || t.pr_url.toLowerCase().includes(search.toLowerCase()) || (t.summary?.toLowerCase().includes(search.toLowerCase()))
    const matchStatus = !statusFilter || t.status === statusFilter
    return matchSearch && matchStatus
  })

  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage))
  const paged = filtered.slice((page - 1) * perPage, page * perPage)

  return (
    <div className="min-h-screen bg-[#0B1020]">
      <Navbar onNavigate={onNavigate} />
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-[#E2E8F0]">Task History</h1>
            <p className="text-sm text-[#64748B]">{mockTasks.length} total reviews</p>
          </div>
        </div>

        <div className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
            <input
              placeholder="Search by PR URL or title..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              className="w-full h-10 pl-9 pr-3 rounded-md border border-[#1E2A45] bg-[#0B1020] text-sm text-[#E2E8F0] placeholder:text-[#64748B] focus:outline-none focus:ring-2 focus:ring-[#38BDF8]/40"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="h-10 px-3 rounded-md border border-[#1E2A45] bg-[#0B1020] text-sm text-[#E2E8F0] focus:outline-none focus:ring-2 focus:ring-[#38BDF8]/40"
          >
            <option value="">All Status</option>
            <option value="DONE">Done</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">Pending</option>
          </select>
        </div>

        <Card className="glass-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>PR</TableHead>
                <TableHead>Risk</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-[#64748B] py-8">No tasks found</TableCell>
                </TableRow>
              ) : paged.map((task) => {
                const st = statusConfig[task.status] || { color: "text-gray-400", icon: Clock, label: task.status }
                const Icon = st.icon
                return (
                  <TableRow key={task.id}>
                    <TableCell className="font-mono text-xs">#{task.id}</TableCell>
                    <TableCell>
                      <div className="text-sm text-[#E2E8F0] truncate max-w-[250px]">{task.summary || task.pr_url}</div>
                      <div className="text-xs text-[#64748B] truncate max-w-[250px]">{task.pr_url}</div>
                    </TableCell>
                    <TableCell>
                      {task.risk_level !== "-" ? (
                        <span className={`text-xs px-1.5 py-0.5 rounded border ${riskBadge[task.risk_level] || riskBadge.LOW}`}>
                          {task.risk_level}
                        </span>
                      ) : (
                        <span className="text-xs text-[#64748B]">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center gap-1 text-xs ${st.color}`}>
                        <Icon className="w-3 h-3" />
                        {st.label}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-[#64748B]">{task.created_at}</TableCell>
                    <TableCell>
                      {task.status === "DONE" && (
                        <Button size="sm" variant="ghost" className="h-7 text-xs text-[#38BDF8] hover:bg-[#38BDF8]/5"
                          onClick={() => onViewReport(task.id)}>
                          Report
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 text-xs text-[#64748B]">
            <span>Page {page} of {totalPages}</span>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" className="border-[#1E2A45] h-8 w-8 p-0"
                disabled={page <= 1} onClick={() => setPage(page - 1)}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" className="border-[#1E2A45] h-8 w-8 p-0"
                disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
