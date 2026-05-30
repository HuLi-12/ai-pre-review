import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Shield, Search, Bug, Terminal, Key, Database, Shuffle, TestTube, FileText, AlertTriangle } from "lucide-react"

const rules = [
  { id: "S001", name: "hardcoded_print", severity: "high", detection: "static", description: "检测遗留的调试输出语句，如 print、console.log、System.out.println 等。这些语句不应出现在生产代码中。", bad_code: 'print("debug:", data)\nconsole.log("user:", user)', good_code: "import logging\nlogger = logging.getLogger(__name__)\nlogger.debug(\"user: %s\", user)" },
  { id: "S002", name: "todo_fixme", severity: "low", detection: "static", description: "检测代码中遗留的 TODO 或 FIXME 注释。建议在合并前确认这些待办项是否已处理。", bad_code: "# TODO: handle edge case\n// FIXME: this is a hack", good_code: "# 已处理或创建 Issue 跟踪" },
  { id: "S003", name: "empty_catch", severity: "high", detection: "static", description: "检测空的 catch 块。异常被静默吞掉会导致难以排查的 Bug，至少应记录异常信息。", bad_code: "try:\n    do_something()\nexcept Exception:\n    pass", good_code: "try:\n    do_something()\nexcept Exception as e:\n    logger.error(\"failed: %s\", e)" },
  { id: "S004", name: "sensitive_log", severity: "high", detection: "static", description: "检测是否在日志中记录了敏感信息（密码、密钥、Token 等）。避免将凭据写入日志。", bad_code: 'logger.info("password: %s", password)', good_code: 'logger.info("login success: user=%s", user)' },
  { id: "S005", name: "hardcoded_password", severity: "critical", detection: "static", description: "检测硬编码的密码、密钥或 API Token。凭据应通过环境变量或密钥管理服务注入。", bad_code: 'password = "123456"\napi_key = "sk-xxxxx"', good_code: 'password = os.getenv("DB_PASSWORD")\napi_key = os.getenv("API_KEY")' },
  { id: "S006", name: "missing_null_check", severity: "medium", detection: "ai", description: "检测方法调用结果是否缺少空值检查。由 AI 分析调用链判断可能为空的返回值。", bad_code: "user = get_user(id)\nuser.name  # user may be None", good_code: "user = get_user(id)\nif user:\n    print(user.name)" },
  { id: "S007", name: "large_method", severity: "medium", detection: "static", description: "检测被 PR 修改的方法是否过长（超过 80 行）。过长的方法应当拆分为多个小函数。", bad_code: "# > 80 lines in one method", good_code: "# Split into smaller helper functions" },
  { id: "S008", name: "missing_auth_check", severity: "high", detection: "static", description: "检测新增的 API 端点是否缺少身份验证/授权注解。所有新 API 应确保有权限控制。", bad_code: '@app.post("/admin/delete")\ndef delete_user():  # no auth!', good_code: '@app.post("/admin/delete")\n@require_auth\ndef delete_user():' },
  { id: "S009", name: "missing_validation", severity: "medium", detection: "static", description: "检测新增 API 端点是否缺少参数校验注解（@Valid、@NotNull 等）。", bad_code: '@app.post("/user")\ndef create_user(name: str):  # no validation', good_code: '@app.post("/user")\ndef create_user(@NotBlank name: str):' },
  { id: "S010", name: "broad_exception", severity: "high", detection: "static", description: "检测是否捕获了过于宽泛的异常（Exception 或 Throwable）。应捕获具体异常类型。", bad_code: "try:\n    process()\nexcept Exception:\n    pass", good_code: "try:\n    process()\nexcept ValueError:\n    handle_value_error()" },
  { id: "S011", name: "loop_db_call", severity: "high", detection: "static", description: "检测循环体内是否包含数据库查询或 API 调用，可能导致 N+1 性能问题。", bad_code: "for user_id in ids:\n    user = db.query(User).get(user_id)", good_code: "users = db.query(User).filter(User.id.in_(ids)).all()" },
  { id: "S012", name: "no_pagination", severity: "medium", detection: "ai", description: "检测列表查询接口是否缺少分页或 LIMIT 限制。无分页的查询可能导致性能问题或 OOM。", bad_code: '@app.get("/users")\ndef list_users():\n    return db.query(User).all()', good_code: '@app.get("/users")\ndef list_users(page: int, size: int):\n    return db.query(User).offset(page).limit(size).all()' },
  { id: "S013", name: "transaction_risk", severity: "high", detection: "ai", description: "检测一个方法内多次数据库写操作但缺少事务包裹。多步写入应放在同一事务中。", bad_code: "def transfer():\n    db.execute(\"UPDATE account SET ...\")\n    db.execute(\"UPDATE account SET ...\")", good_code: "def transfer():\n    with db.transaction():\n        db.execute(\"UPDATE account SET ...\")\n        db.execute(\"UPDATE account SET ...\")" },
  { id: "S014", name: "unsafe_delete_or_update", severity: "critical", detection: "static", description: "检测 SQL 的 DELETE/UPDATE 语句是否缺少 WHERE 条件。无条件的更新/删除可能导致数据丢失。", bad_code: "DELETE FROM users\nUPDATE account SET balance = 0", good_code: "DELETE FROM users WHERE id = ?\nUPDATE account SET balance = 0 WHERE id = ?" },
  { id: "S015", name: "test_missing", severity: "medium", detection: "ai", description: "核心源码文件变更但对应的测试文件未更新。建议为新增/修改的逻辑补充测试用例。", bad_code: "Modified: src/service.py  (no test update)", good_code: "Modified: src/service.py, tests/test_service.py" },
]

const severityConfig: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  medium: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  low: "bg-gray-500/10 text-gray-400 border-gray-500/20",
}

const ruleIcons: Record<string, React.ElementType> = {
  S001: Terminal, S002: FileText, S003: Bug, S004: Key, S005: Key,
  S006: AlertTriangle, S007: FileText, S008: Shield, S009: Shield, S010: AlertTriangle,
  S011: Database, S012: Database, S013: Shuffle, S014: AlertTriangle, S015: TestTube,
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
          <span className="hover:text-[#E2E8F0] cursor-pointer transition" onClick={() => onNavigate("history")}>History</span>
          <span className="text-[#E2E8F0] cursor-pointer transition">Rules</span>
        </div>
      </div>
    </nav>
  )
}

export default function RulesPage({ onNavigate }: { onNavigate: (page: string) => void }) {
  const [search, setSearch] = useState("")
  const [severityFilter, setSeverityFilter] = useState("all")

  const filtered = rules.filter((r) => {
    const matchSearch = !search || r.id.toLowerCase().includes(search.toLowerCase()) || r.name.toLowerCase().includes(search.toLowerCase()) || r.description.toLowerCase().includes(search.toLowerCase())
    const matchSeverity = severityFilter === "all" || r.severity === severityFilter
    return matchSearch && matchSeverity
  })

  return (
    <div className="min-h-screen bg-[#0B1020]">
      <Navbar onNavigate={onNavigate} />
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-[#E2E8F0]">Review Rules</h1>
            <p className="text-sm text-[#64748B]">{rules.length} rules · {rules.filter(r => r.severity === "critical" || r.severity === "high").length} critical/high</p>
          </div>
        </div>

        <div className="flex gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
            <input
              placeholder="Search rules..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-10 pl-9 pr-3 rounded-md border border-[#1E2A45] bg-[#0B1020] text-sm text-[#E2E8F0] placeholder:text-[#64748B] focus:outline-none focus:ring-2 focus:ring-[#38BDF8]/40"
            />
          </div>
          <div className="flex gap-1.5">
            {["all", "critical", "high", "medium", "low"].map((s) => (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition ${
                  severityFilter === s
                    ? "border-[#38BDF8]/40 bg-[#38BDF8]/10 text-[#38BDF8]"
                    : "border-[#1E2A45] text-[#64748B] hover:text-[#E2E8F0]"
                }`}
              >
                {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          {filtered.map((rule) => {
            const Icon = ruleIcons[rule.id] || AlertTriangle
            return (
              <Card key={rule.id} className="glass-card group">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className="p-1.5 rounded-lg bg-[#38BDF8]/5 mt-0.5">
                      <Icon className="w-4 h-4 text-[#38BDF8]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-[#E2E8F0]">{rule.id}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded border ${severityConfig[rule.severity]}`}>
                          {rule.severity.toUpperCase()}
                        </span>
                        <span className="text-xs text-[#64748B] font-mono">{rule.name}</span>
                        {rule.detection === "ai" && (
                          <span className="text-xs text-[#38BDF8] border border-[#38BDF8]/20 px-1.5 py-0.5 rounded">AI</span>
                        )}
                      </div>
                      <p className="text-xs text-[#94A3B8] mb-3">{rule.description}</p>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <div className="p-2 rounded bg-red-500/5 border border-red-500/10">
                          <div className="text-[0.6rem] text-red-400 uppercase tracking-wider mb-1">Bad</div>
                          <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap">{rule.bad_code}</pre>
                        </div>
                        <div className="p-2 rounded bg-emerald-500/5 border border-emerald-500/10">
                          <div className="text-[0.6rem] text-emerald-400 uppercase tracking-wider mb-1">Good</div>
                          <pre className="text-xs text-emerald-300 font-mono whitespace-pre-wrap">{rule.good_code}</pre>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-[#64748B] text-sm">No rules match your search</div>
          )}
        </div>
      </div>
    </div>
  )
}
