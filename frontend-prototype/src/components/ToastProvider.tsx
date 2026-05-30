import { createContext, useContext, useState, useCallback } from "react"
import { X, CheckCheck, AlertTriangle, Info } from "lucide-react"

type ToastType = "success" | "error" | "info"

interface Toast {
  id: number
  type: ToastType
  message: string
}

interface ToastContextType {
  toast: (type: ToastType, message: string) => void
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

const icons: Record<ToastType, React.ElementType> = {
  success: CheckCheck,
  error: AlertTriangle,
  info: Info,
}

const colors: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", icon: "text-emerald-400" },
  error: { bg: "bg-red-500/10", border: "border-red-500/20", icon: "text-red-400" },
  info: { bg: "bg-[#38BDF8]/10", border: "border-[#38BDF8]/20", icon: "text-[#38BDF8]" },
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  let nextId = 0

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = nextId++
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }, [])

  const removeToast = (id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => {
          const Icon = icons[t.type]
          const c = colors[t.type]
          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-center gap-2 px-3 py-2 rounded-lg border ${c.bg} ${c.border} shadow-lg animate-in slide-in-from-right`}
              style={{ animation: "slideIn 0.2s ease-out" }}
            >
              <Icon className={`w-4 h-4 ${c.icon} shrink-0`} />
              <span className="text-xs text-[#E2E8F0]">{t.message}</span>
              <button onClick={() => removeToast(t.id)} className="ml-2 text-[#64748B] hover:text-[#E2E8F0]">
                <X className="w-3 h-3" />
              </button>
            </div>
          )
        })}
      </div>
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(100%); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastContext.Provider>
  )
}
