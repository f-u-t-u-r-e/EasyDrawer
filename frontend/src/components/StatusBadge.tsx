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

  const colors = {
    idle: 'text-slate-400',
    loading: 'text-blue-400 animate-spin',
    success: 'text-green-400',
    error: 'text-red-400',
  }

  const Icon = icons[status]

  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className={`w-4 h-4 ${colors[status]}`} />
      <span className="text-slate-300 flex-1">{text}</span>
      {progress !== undefined && progress > 0 && (
        <div className="w-20 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(100, progress * 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}
