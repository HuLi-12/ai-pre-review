import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Shield, GitPullRequest, Brain, Target, CheckCheck, ChevronRight, Sparkles, ArrowRight, Zap, AlertTriangle } from "lucide-react"

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
          <span className="text-[#E2E8F0] cursor-pointer transition">Home</span>
          <span className="hover:text-[#E2E8F0] cursor-pointer transition" onClick={() => onNavigate("history")}>History</span>
          <span className="hover:text-[#E2E8F0] cursor-pointer transition" onClick={() => onNavigate("rules")}>Rules</span>
        </div>
      </div>
    </nav>
  )
}

function DemoScenarioCard({ title, desc, icon: Icon, onClick }: { title: string; desc: string; icon: React.ElementType; onClick: () => void }) {
  return (
    <div className="glass-card p-4 cursor-pointer group hover:border-[#38BDF8]/40 transition-all" onClick={onClick}>
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-[#38BDF8]/5">
          <Icon className="w-5 h-5 text-[#38BDF8]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[#E2E8F0]">{title}</div>
          <div className="text-xs text-[#64748B] truncate">{desc}</div>
        </div>
        <ChevronRight className="w-4 h-4 text-[#64748B] group-hover:text-[#38BDF8] transition-colors shrink-0" />
      </div>
    </div>
  )
}

function FeatureCard({ icon: Icon, title, desc, accent }: { icon: React.ElementType; title: string; desc: string; accent?: string }) {
  return (
    <Card className="glass-card group hover:border-[#38BDF8]/20 transition-all">
      <CardContent className="p-4">
        <div className={`p-2 rounded-lg w-fit mb-3 bg-[#38BDF8]/5`}>
          <Icon className={`w-5 h-5 ${accent || "text-[#38BDF8]"}`} />
        </div>
        <h3 className="text-sm font-semibold text-[#E2E8F0] mb-1">{title}</h3>
        <p className="text-xs text-[#64748B]">{desc}</p>
      </CardContent>
    </Card>
  )
}

export default function HomePage({ onNavigate, onStartReview }: { onNavigate: (page: string) => void; onStartReview: (taskId?: number) => void }) {
  const [prUrl, setPrUrl] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (prUrl.trim()) {
      // In a real app, this would POST /api/tasks and navigate to the dashboard
      onStartReview(undefined)
    }
  }

  return (
    <div className="min-h-screen bg-[#0B1020]">
      <Navbar onNavigate={onNavigate} />
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-[#38BDF8]/20 bg-[#38BDF8]/5 text-[#38BDF8] text-xs font-medium mb-4">
            <Sparkles className="w-3 h-3" />
            AI-Powered Code Review Assistant
          </div>
          <h1 className="text-4xl font-bold text-[#E2E8F0] mb-3">
            Smart PR Reviews,{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#38BDF8] to-[#818CF8]">
              Powered by AI
            </span>
          </h1>
          <p className="text-[#64748B] max-w-xl mx-auto text-sm">
            Static rule scanning + AI deep analysis. Catch bugs, security issues, and code quality problems before they ship.
          </p>
        </div>

        {/* Input */}
        <Card className="glass-card max-w-2xl mx-auto mb-8">
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-[#E2E8F0] mb-1.5 block">GitHub PR URL</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="https://github.com/org/repo/pull/42"
                    value={prUrl}
                    onChange={(e) => setPrUrl(e.target.value)}
                    className="flex-1"
                  />
                  <Button type="submit" className="bg-[#38BDF8] text-[#0B1020] hover:bg-[#38BDF8]/90 font-semibold shrink-0">
                    <Zap className="w-4 h-4 mr-1.5" />
                    Review
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-[#64748B]">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input type="checkbox" className="accent-[#38BDF8]" />
                  Auto-comment on PR
                </label>
                <span>No GitHub token required for public repos</span>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Pipeline Preview */}
        <Card className="glass-card max-w-2xl mx-auto mb-12">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              {[
                { label: "Raw Output", count: "18", icon: Brain },
                { label: "Deduped", count: "9", icon: Target },
                { label: "Visible", count: "6", icon: CheckCheck },
                { label: "GitHub Ready", count: "4", icon: GitPullRequest },
              ].map((step, i) => (
                <div key={step.label} className="flex items-center gap-1 flex-1">
                  <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border
                    ${i === 3 ? "border-emerald-500/40 bg-emerald-500/5 text-emerald-400" : "border-[#1E2A45] bg-[#131A2E] text-[#64748B]"}`}>
                    <step.icon className="w-3 h-3" />
                    <span>{step.count}</span>
                    <span className="hidden sm:inline">{step.label}</span>
                  </div>
                  {i < 3 && <ArrowRight className="w-4 h-4 text-[#1E2A45] shrink-0" />}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Features */}
        <h2 className="text-lg font-semibold text-[#E2E8F0] mb-4">Why AI Review Cockpit?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
          <FeatureCard icon={Shield} title="15 Static Rules" desc="Hardcoded secrets, N+1 queries, missing auth, unsafe SQL, and more." />
          <FeatureCard icon={Brain} title="AI Deep Analysis" desc="Context-aware cross-file review with evidence chain and confidence scoring." />
          <FeatureCard icon={Target} title="Noise Filter" desc="Dedup + confidence gate: from 18 raw findings to 4 GitHub-ready issues." />
        </div>

        {/* Demo Scenarios */}
        <h2 className="text-lg font-semibold text-[#E2E8F0] mb-4">Quick Demo</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <DemoScenarioCard
            title="High Risk PR"
            desc="Order batch processing — 1 critical, 3 high findings"
            icon={AlertTriangle}
            onClick={() => onStartReview(142)}
          />
          <DemoScenarioCard
            title="Clean PR"
            desc="README update — no findings"
            icon={CheckCheck}
            onClick={() => onStartReview(143)}
          />
        </div>
      </div>
    </div>
  )
}
