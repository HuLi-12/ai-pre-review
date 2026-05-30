import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { mockReport, mockFindings, mockFiles, type Finding } from "@/lib/mock-data"
import {
  Shield, AlertTriangle, ArrowRight, GitPullRequest, FileText,
  Brain, Target, Layers, Bug, Terminal, Key,
  Database, Shuffle, TestTube, ExternalLink, Copy, CheckCheck,
  ListFilter, Activity, Zap, Eye
} from "lucide-react"

const severityConfig = {
  critical: { color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/20", badge: "bg-red-500/10 text-red-400" },
  high: { color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20", badge: "bg-amber-500/10 text-amber-400" },
  medium: { color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", badge: "bg-blue-500/10 text-blue-400" },
  low: { color: "text-gray-400", bg: "bg-gray-500/10", border: "border-gray-500/20", badge: "bg-gray-500/10 text-gray-400" },
}

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = severityConfig[severity as keyof typeof severityConfig] || severityConfig.low
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded ${cfg.badge} border ${cfg.border}`}>
      {severity.toUpperCase()}
    </span>
  )
}

function Navbar() {
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
          <span className="hover:text-[#E2E8F0] cursor-pointer transition">Dashboard</span>
          <span className="hover:text-[#E2E8F0] cursor-pointer transition">History</span>
          <span className="hover:text-[#E2E8F0] cursor-pointer transition">Rules</span>
          <Button variant="outline" size="sm" className="border-[#1E2A45] text-[#E2E8F0] hover:bg-[#1E2A45]">
            <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
            View PR
          </Button>
        </div>
      </div>
    </nav>
  )
}

function MetricCard({ icon: Icon, label, value, sub, accent }: {
  icon: React.ElementType; label: string; value: string; sub?: string; accent?: string
}) {
  return (
    <Card className="glass-card flex-1 min-w-[160px]">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <span className="text-xs text-[#64748B] uppercase tracking-wider">{label}</span>
          <Icon className={`w-4 h-4 ${accent || "text-[#64748B]"}`} />
        </div>
        <div className={`text-2xl font-bold ${accent || "text-[#E2E8F0]"}`}>{value}</div>
        {sub && <div className="text-xs text-[#64748B] mt-1">{sub}</div>}
      </CardContent>
    </Card>
  )
}

function PipelineBar() {
  const r = mockReport
  const stages = [
    { label: "Raw AI", count: r.total_raw, icon: Brain },
    { label: "Deduped", count: r.total_deduped, icon: Layers },
    { label: "Visible", count: r.total_visible, icon: Eye },
    { label: "GitHub Ready", count: r.total_github_ready, icon: CheckCheck },
  ]
  return (
    <Card className="glass-card">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#38BDF8]" />
            <span className="text-xs font-medium text-[#E2E8F0] uppercase tracking-wider">Results Pipeline</span>
          </div>
          <span className="text-xs text-[#64748B]">Confidence Threshold ≥ 0.60</span>
        </div>
        <div className="flex items-center justify-between">
          {stages.map((stage, i) => (
            <div key={stage.label} className="flex items-center gap-1 flex-1">
              <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border
                ${i === stages.length - 1
                  ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-400"
                  : "border-[#1E2A45] bg-[#131A2E] text-[#64748B]"}`}>
                <stage.icon className="w-3 h-3" />
                <span>{stage.count}</span>
                <span className="hidden sm:inline">{stage.label}</span>
              </div>
              {i < stages.length - 1 && <ArrowRight className="w-4 h-4 text-[#1E2A45] shrink-0" />}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function FileRiskMap() {
  return (
    <Card className="glass-card">
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#38BDF8]" />
            <CardTitle className="text-xs font-medium text-[#E2E8F0] uppercase tracking-wider">File Risk Map</CardTitle>
          </div>
          <span className="text-xs text-[#64748B]">{mockFiles.filter(f => f.analysis_depth !== 'skip').length} analyzed</span>
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-0 space-y-2">
        {mockFiles.map(file => {
          const severity = file.risk_level
          const cfg = severityConfig[severity as keyof typeof severityConfig]
          const riskColor = severity === "critical" ? "#EF4444" : severity === "high" ? "#F59E0B" : severity === "medium" ? "#3B82F6" : "#6B7280"
          const findingsCount = mockFindings.filter(f => f.file_path === file.file_path).length
          return (
            <div key={file.id} className="group cursor-pointer">
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0`} style={{ backgroundColor: riskColor }} />
                  <span className="text-[#E2E8F0] truncate">{file.file_path}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-2">
                  <span className={`text-${severity === 'low' ? 'gray' : severity === 'medium' ? 'blue' : severity === 'high' ? 'amber' : 'red'}-400 font-medium`}>{file.risk_score}%</span>
                  <span className="text-[#64748B]">+{file.additions}/-{file.deletions}</span>
                </div>
              </div>
              <div className="risk-bar">
                <div className="risk-bar-fill" style={{ width: `${file.risk_score}%`, backgroundColor: riskColor }} />
              </div>
              <div className="flex gap-2 mt-1">
                {findingsCount > 0 && (
                  <span className={`text-[10px] ${cfg.color}`}>{findingsCount} finding{findingsCount > 1 ? 's' : ''}</span>
                )}
                <span className="text-[10px] text-[#64748B]">{file.analysis_depth} scan</span>
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

function EvidenceChain({ evidence }: { evidence: Finding["evidence"] }) {
  if (!evidence?.length) return null
  return (
    <div className="mb-2 p-2 rounded" style={{ background: "rgba(148,163,184,0.04)", border: "1px solid rgba(148,163,184,0.1)" }}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <Layers className="w-3 h-3 text-[#64748B]" />
        <span className="text-[0.65rem] text-[#64748B] uppercase tracking-wider">Evidence Chain</span>
      </div>
      <div className="flex flex-wrap gap-0">
        {evidence.map((ev, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-[0.7rem] px-2 py-0.5 border-r border-[rgba(148,163,184,0.15)] last:border-r-0">
            <span className="text-[#64748B]">{ev.label}:</span>
            <span className="text-[#E2E8F0]">{ev.content}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function FindingCard({ finding }: { finding: Finding }) {
  const severity = finding.severity
  const cfg = severityConfig[severity as keyof typeof severityConfig]
  const typeIcon = finding.finding_type?.startsWith("S")
    ? { S001: Bug, S002: Terminal, S008: Key, S011: Database, S013: Shuffle, S014: AlertTriangle }
    : { default: Bug }
  const Icon = (typeIcon as any)[finding.finding_type] || Bug

  return (
    <div className={`rounded-lg border ${cfg.border} ${cfg.bg} p-4`}>
      <div className="flex items-start gap-3">
        <div className={`mt-0.5`}>
          <Icon className={`w-4 h-4 ${cfg.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <SeverityBadge severity={severity} />
            {finding.finding_type && (
              <span className="text-[0.65rem] font-mono text-[#64748B] border border-[#1E2A45] px-1.5 py-0.5 rounded">
                {finding.finding_type}
              </span>
            )}
            <span className="text-[0.65rem] text-[#64748B]">
              {(finding.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          <h4 className="text-sm font-medium text-[#E2E8F0] mb-1">{finding.title}</h4>
          <p className="text-xs text-[#94A3B8] mb-2">{finding.reason}</p>

          <EvidenceChain evidence={finding.evidence} />

          <div className="flex items-center gap-2">
            <span className="text-xs text-[#64748B] font-mono">{finding.file_path}:{finding.line_number}</span>
          </div>

          <div className="mt-2 flex items-start gap-2 p-2 rounded bg-[#0B1020]/50">
            <Zap className="w-3 h-3 text-[#38BDF8] mt-0.5 shrink-0" />
            <span className="text-xs text-[#94A3B8]">{finding.suggestion}</span>
          </div>

          <div className="flex gap-2 mt-3">
            <Button size="sm" variant="ghost" className="h-7 text-xs text-[#64748B] hover:text-[#38BDF8] hover:bg-[#38BDF8]/5">
              <Copy className="w-3 h-3 mr-1" /> Copy
            </Button>
            <Button size="sm" variant="ghost" className="h-7 text-xs text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/5">
              <CheckCheck className="w-3 h-3 mr-1" /> Resolve
            </Button>
            <Button size="sm" variant="ghost" className="h-7 text-xs text-amber-400 hover:text-amber-300 hover:bg-amber-500/5">
              False Positive
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ReviewDecisionCard() {
  const r = mockReport
  const isCritical = r.risk_level === "CRITICAL"
  const isHigh = r.risk_level === "HIGH"
  const borderColor = isCritical ? "border-red-500/30" : isHigh ? "border-amber-500/30" : "border-emerald-500/30"
  const accentColor = isCritical ? "text-red-400" : isHigh ? "text-amber-400" : "text-emerald-400"
  const IconComponent = isCritical ? AlertTriangle : isHigh ? AlertTriangle : CheckCheck

  return (
    <Card className={`glass-card ${borderColor}`}>
      <CardContent className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className={`p-2 rounded-lg ${isCritical ? "bg-red-500/10" : isHigh ? "bg-amber-500/10" : "bg-emerald-500/10"}`}>
            <IconComponent className={`w-5 h-5 ${accentColor}`} />
          </div>
          <div>
            <div className={`text-sm font-semibold ${accentColor}`}>Review Decision</div>
            <div className="text-xs text-[#64748B]">{r.merge_suggestion}</div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-[#64748B]">Risk Level</span>
            <SeverityBadge severity={r.risk_level.toLowerCase()} />
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-[#64748B]">Review Confidence</span>
            <span className="text-[#E2E8F0] font-mono">{r.review_confidence}%</span>
          </div>
          <Progress value={r.review_confidence} className="h-1.5" />
        </div>
        {r.key_focus_points.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#1E2A45]">
            <div className="text-xs text-[#64748B] mb-2 uppercase tracking-wider">Key Focus Points</div>
            <div className="space-y-1.5">
              {r.key_focus_points.map((point, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-[#94A3B8]">
                  <div className="w-1 h-1 rounded-full bg-[#38BDF8] mt-1.5 shrink-0" />
                  {point}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function SummaryCard() {
  const r = mockReport
  return (
    <Card className="glass-card">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <GitPullRequest className="w-4 h-4 text-[#38BDF8]" />
          <span className="text-xs font-medium text-[#E2E8F0] uppercase tracking-wider">PR Summary</span>
        </div>
        <p className="text-sm text-[#94A3B8] mb-3">{r.summary}</p>
        <div className="flex items-center gap-4 text-xs text-[#64748B]">
          <a href={r.pr_url} className="flex items-center gap-1 hover:text-[#38BDF8] transition" target="_blank">
            <ExternalLink className="w-3 h-3" />
            #{r.task_id}
          </a>
          <span>{r.pr_title}</span>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ReviewDashboard() {
  const groupedFindings = {
    critical: mockFindings.filter(f => f.severity === "critical"),
    high: mockFindings.filter(f => f.severity === "high"),
    medium: mockFindings.filter(f => f.severity === "medium"),
    low: mockFindings.filter(f => f.severity === "low"),
  }

  return (
    <div className="min-h-screen bg-[#0B1020]">
      <Navbar />
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-[#E2E8F0]">Review Dashboard</h1>
            <p className="text-sm text-[#64748B]">PR #{mockReport.task_id} — {mockReport.pr_title}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="border-[#1E2A45] text-[#E2E8F0] hover:bg-[#1E2A45]">
              <ListFilter className="w-3.5 h-3.5 mr-1.5" />
              Filter
            </Button>
            <Button size="sm" className="bg-[#38BDF8] text-[#0B1020] hover:bg-[#38BDF8]/90 font-semibold">
              <Target className="w-3.5 h-3.5 mr-1.5" />
              Start Review
            </Button>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="flex gap-4 mb-4 flex-wrap">
          <MetricCard icon={Shield} label="Risk Level" value={mockReport.risk_level} sub={mockReport.merge_suggestion} accent="text-amber-400" />
          <MetricCard icon={Brain} label="Review Confidence" value={`${mockReport.review_confidence}%`} sub="AI + Static hybrid" accent="text-[#38BDF8]" />
          <MetricCard icon={AlertTriangle} label="Findings" value={`${mockFindings.filter(f => f.severity === "critical" || f.severity === "high").length} critical/high`} sub={`${mockFindings.length} total`} accent="text-red-400" />
          <MetricCard icon={CheckCheck} label="Merge Decision" value={mockReport.risk_level} sub={mockReport.merge_suggestion} accent={mockReport.risk_level === "HIGH" ? "text-amber-400" : "text-emerald-400"} />
        </div>

        {/* Pipeline */}
        <div className="mb-4">
          <PipelineBar />
        </div>

        {/* Main Content: 3 columns */}
        <div className="grid grid-cols-12 gap-4">
          {/* Left: File Risk Map */}
          <div className="col-span-12 lg:col-span-3">
            <FileRiskMap />
          </div>

          {/* Center: Findings */}
          <div className="col-span-12 lg:col-span-6">
            {/* Summary */}
            <div className="mb-4">
              <SummaryCard />
            </div>

            {/* Findings Tabs */}
            <Card className="glass-card">
              <CardContent className="p-4">
                <Tabs defaultValue="all" className="w-full">
                  <TabsList className="bg-[#1E2A45]/50 border border-[#1E2A45] mb-4">
                    <TabsTrigger value="all" className="text-[#64748B] data-[state=active]:bg-[#131A2E] data-[state=active]:text-[#E2E8F0]">
                      All ({mockFindings.length})
                    </TabsTrigger>
                    <TabsTrigger value="critical" className="text-[#64748B] data-[state=active]:bg-[#131A2E] data-[state=active]:text-red-400">
                      Critical ({groupedFindings.critical.length})
                    </TabsTrigger>
                    <TabsTrigger value="high" className="text-[#64748B] data-[state=active]:bg-[#131A2E] data-[state=active]:text-amber-400">
                      High ({groupedFindings.high.length})
                    </TabsTrigger>
                    <TabsTrigger value="medium" className="text-[#64748B] data-[state=active]:bg-[#131A2E] data-[state=active]:text-blue-400">
                      Medium ({groupedFindings.medium.length})
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="all" className="space-y-3 mt-0">
                    {mockFindings.map(f => <FindingCard key={f.id} finding={f} />)}
                  </TabsContent>
                  {Object.entries(groupedFindings).map(([sev, findings]) => (
                    <TabsContent key={sev} value={sev} className="space-y-3 mt-0">
                      {findings.length === 0 ? (
                        <div className="text-center py-8 text-[#64748B] text-sm">
                          No {sev} severity findings
                        </div>
                      ) : findings.map(f => <FindingCard key={f.id} finding={f} />)}
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
          </div>

          {/* Right: Review Decision + Test Suggestions */}
          <div className="col-span-12 lg:col-span-3 space-y-4">
            <ReviewDecisionCard />
            {mockReport.test_suggestions.length > 0 && (
              <Card className="glass-card">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <TestTube className="w-4 h-4 text-[#38BDF8]" />
                    <span className="text-xs font-medium text-[#E2E8F0] uppercase tracking-wider">Test Suggestions</span>
                  </div>
                  <div className="space-y-2">
                    {mockReport.test_suggestions.map((s, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-[#94A3B8]">
                        <div className="w-1 h-1 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                        {s}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
