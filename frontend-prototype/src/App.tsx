import { useState } from "react"
import ReviewDashboard from "@/components/ReviewDashboard"
import HomePage from "@/components/HomePage"
import TaskHistoryPage from "@/components/TaskHistoryPage"
import RulesPage from "@/components/RulesPage"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ToastProvider } from "@/components/ToastProvider"

type Page = "home" | "dashboard" | "history" | "rules"

function App() {
  const params = new URLSearchParams(window.location.search)
  const taskIdParam = params.get("taskId")
  const initialPage = taskIdParam ? "dashboard" : "home"

  const [page, setPage] = useState<Page>(initialPage as Page)
  const [activeTaskId, setActiveTaskId] = useState<number | undefined>(
    taskIdParam ? Number(taskIdParam) : undefined
  )

  const handleStartReview = (taskId?: number) => {
    setActiveTaskId(taskId)
    setPage("dashboard")
  }

  const handleViewReport = (taskId: number) => {
    setActiveTaskId(taskId)
    setPage("dashboard")
  }

  const navigate = (p: string) => setPage(p as Page)

  return (
    <ErrorBoundary>
      <ToastProvider>
        {page === "dashboard" && <ReviewDashboard taskId={activeTaskId} useMock={!activeTaskId} />}
        {page === "history" && <TaskHistoryPage onNavigate={navigate} onViewReport={handleViewReport} />}
        {page === "rules" && <RulesPage onNavigate={navigate} />}
        {page === "home" && <HomePage onNavigate={navigate} onStartReview={handleStartReview} />}
      </ToastProvider>
    </ErrorBoundary>
  )
}

export default App
