import { useState, useEffect, useCallback } from "react"
import type { Finding, ChangedFile, TaskReport } from "@/lib/types"
import { fetchReport, fetchFiles, submitFeedback } from "@/lib/api"

interface ReportState {
  loading: boolean
  error: string | null
  report: TaskReport | null
  findings: Finding[]
  files: ChangedFile[]
}

export function useReport(taskId: number | null) {
  const [state, setState] = useState<ReportState>({
    loading: false,
    error: null,
    report: null,
    findings: [],
    files: [],
  })

  const load = useCallback(async () => {
    if (!taskId) return
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const [reportData, filesData] = await Promise.all([
        fetchReport(taskId),
        fetchFiles(taskId),
      ])
      setState({
        loading: false,
        error: null,
        report: reportData.report,
        findings: reportData.findings,
        files: filesData,
      })
    } catch (err: any) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err.message ?? "Failed to load report",
      }))
    }
  }, [taskId])

  useEffect(() => {
    load()
  }, [load])

  const handleFeedback = useCallback(
    async (findingId: number, type: "FALSE_POSITIVE" | "EFFECTIVE" | "RESOLVED") => {
      try {
        await submitFeedback(findingId, type)
        setState((s) => ({
          ...s,
          findings: s.findings.map((f) =>
            f.id === findingId ? { ...f, status: type === "RESOLVED" ? "RESOLVED" : type === "FALSE_POSITIVE" ? "DISMISSED" : f.status } : f
          ),
        }))
      } catch (err: any) {
        console.error("Feedback failed", err)
      }
    },
    []
  )

  return { ...state, reload: load, handleFeedback }
}
