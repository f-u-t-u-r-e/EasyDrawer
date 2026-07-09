import React from 'react'
import { Wand2, Loader2, CheckCircle2, XCircle } from 'lucide-react'

interface StatusBadgeProps {
  status: 'idle' | 'loading' | 'success' | 'error'
  text: string
  progress?: number
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, text, progress }) => {
  const icons = {
    idle: Wand2,
    loading: Loader2,
    success: CheckCircle2,
    error: XCircle,
  }

  const colorMap = {
    idle: { icon: 'text-slate-600', text: 'text-slate-500' },
    loading: { icon: 'text-amber-400 animate-spin', text: 'text-slate-200' },
    success: { icon: 'text-teal-400', text: 'text-slate-400' },
    error: { icon: 'text-rose-400', text: 'text-rose-300' },
  }

  const Icon = icons[status]
  const colors = colorMap[status]

  return (
    <div className="flex items-center gap-2.5 text-sm">
      <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${colors.icon}`} />
      <span className={`flex-1 truncate ${colors.text}`}>{text}</span>
      {progress !== undefined && progress > 0 && (
        <div className="progress-bar w-16">
          <div
            className="progress-bar-fill"
            style={{ width: `${Math.min(100, progress * 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}
