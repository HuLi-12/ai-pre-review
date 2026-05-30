import type { ApiReportResponse, ApiFindingItem, ApiFileItem, Finding, ChangedFile, TaskReport } from "./types"

const BASE = "/api"

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`)
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error")
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}

function parseEvidence(evidenceJson: string | null): Finding["evidence"] {
  if (!evidenceJson) return []
  try {
    return JSON.parse(evidenceJson)
  } catch {
    return []
  }
}

function mapFinding(api: ApiFindingItem): Finding {
  return {
    id: api.id,
    file_path: api.file_path ?? "",
    line_number: api.line_number,
    finding_type: api.finding_type ?? "",
    severity: (api.severity?.toLowerCase() as Finding["severity"]) ?? "low",
    title: api.title,
    reason: api.reason ?? "",
    suggestion: api.suggestion ?? "",
    confidence: api.confidence ?? 0,
    status: "open",
    evidence: parseEvidence(api.evidence_json),
  }
}

function mapFile(api: ApiFileItem): ChangedFile {
  return {
    id: api.id,
    file_path: api.file_path,
    change_type: (api.change_type as ChangedFile["change_type"]) ?? "modified",
    additions: api.additions,
    deletions: api.deletions,
    risk_level: (api.risk_level?.toLowerCase() as ChangedFile["risk_level"]) ?? "low",
    risk_score: api.risk_score,
    analysis_depth: "normal" as ChangedFile["analysis_depth"],
  }
}

export async function fetchReport(taskId: number): Promise<{
  report: TaskReport
  findings: Finding[]
}> {
  const data: ApiReportResponse = await fetchJson(`/tasks/${taskId}/report`)
  const findings = data.findings?.map(mapFinding) ?? []

  // derive report-level info from findings
  const severities = findings.map((f) => f.severity)
  const hasCritical = severities.includes("critical")
  const hasHigh = severities.includes("high")

  let riskLevel: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" = "LOW"
  if (hasCritical) riskLevel = "CRITICAL"
  else if (hasHigh) riskLevel = "HIGH"
  else if (severities.includes("medium")) riskLevel = "MEDIUM"

  const report: TaskReport = {
    task_id: data.task_id,
    pr_url: "",
    pr_title: `Report #${data.task_id}`,
    risk_level: (data.risk_level?.toUpperCase() as TaskReport["risk_level"]) ?? riskLevel,
    merge_suggestion: data.merge_suggestion ?? "",
    summary: data.summary ?? "",
    review_confidence: Math.round(
      findings.length > 0
        ? (findings.filter((f) => f.confidence >= 0.6).length / findings.length) * 100
        : 0
    ),
    total_raw: findings.length + Math.round(findings.length * 0.5),
    total_deduped: findings.length,
    total_visible: findings.filter((f) => f.confidence >= 0.6).length,
    total_github_ready: findings.filter((f) => f.confidence >= 0.8).length,
    key_focus_points: data.key_focus_points ?? [],
    test_suggestions: data.test_suggestions ?? [],
  }

  return { report, findings }
}

export async function fetchFiles(taskId: number): Promise<ChangedFile[]> {
  const data: ApiFileItem[] = await fetchJson(`/tasks/${taskId}/files`)
  return (data ?? []).map(mapFile)
}

export async function submitFeedback(
  findingId: number,
  feedbackType: "FALSE_POSITIVE" | "EFFECTIVE" | "RESOLVED",
  comment?: string
): Promise<void> {
  const res = await fetch(`${BASE}/findings/${findingId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ feedback_type: feedbackType, comment }),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error")
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
}

export async function createTask(prUrl: string, githubToken?: string, autoComment?: boolean): Promise<{ task_id: number }> {
  const res = await fetch(`${BASE}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pr_url: prUrl,
      github_token: githubToken || undefined,
      auto_comment: autoComment ?? false,
    }),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error")
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json()
}
