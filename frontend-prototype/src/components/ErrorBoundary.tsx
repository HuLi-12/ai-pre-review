import { Component, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { AlertCircle, RefreshCw } from "lucide-react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="min-h-screen bg-[#0B1020] flex items-center justify-center">
          <div className="glass-card max-w-md w-full p-6 text-center">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-[#E2E8F0] mb-2">Something went wrong</h3>
            <p className="text-xs text-[#64748B] mb-4 break-all">
              {this.state.error?.message ?? "An unexpected error occurred"}
            </p>
            <Button
              size="sm"
              variant="outline"
              className="border-[#1E2A45] text-[#E2E8F0]"
              onClick={this.handleRetry}
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Try Again
            </Button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
