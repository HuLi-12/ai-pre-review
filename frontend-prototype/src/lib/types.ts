export interface EvidenceItem {
  type: string
  label: string
  content: string
}

export interface Finding {
  id: number
  file_path: string
  line_number: number | null
  finding_type: string
  severity: "critical" | "high" | "medium" | "low"
  title: string
  reason: string
  suggestion: string
  confidence: number
  status: string
  evidence: EvidenceItem[]
}

export interface ChangedFile {
  id: number
  file_path: string
  change_type: "modified" | "added" | "deleted"
  additions: number
  deletions: number
  risk_level: "critical" | "high" | "medium" | "low"
  risk_score: number
  analysis_depth: "deep" | "normal" | "skip"
}

export interface TaskReport {
  task_id: number
  pr_url: string
  pr_title: string
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  merge_suggestion: string
  summary: string
  review_confidence: number
  total_raw: number
  total_deduped: number
  total_visible: number
  total_github_ready: number
  key_focus_points: string[]
  test_suggestions: string[]
}

export interface ApiReportResponse {
  task_id: number
  summary: string | null
  risk_level: string | null
  merge_suggestion: string | null
  findings: ApiFindingItem[]
  test_suggestions: string[]
  key_focus_points: string[]
}

export interface ApiFindingItem {
  id: number
  file_path: string | null
  line_number: number | null
  finding_type: string | null
  severity: string
  title: string
  reason: string | null
  suggestion: string | null
  confidence: number | null
  evidence_json: string | null
}

export interface ApiFileItem {
  id: number
  file_path: string
  change_type: string
  additions: number
  deletions: number
  risk_level: string
  risk_score: number
}
