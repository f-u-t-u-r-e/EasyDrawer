import React, { useState, useEffect, useCallback } from 'react'
import { History, Trash2, ChevronRight } from 'lucide-react'
import { apiService } from '@/services/api'
import type { HistoryRecord, HistoryListResponse } from '@/types/api'

interface HistoryPanelProps {
  onSelectRecord: (record: HistoryRecord) => void
  refreshTrigger: number
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
  onSelectRecord,
  refreshTrigger,
}) => {
  const [history, setHistory] = useState<HistoryListResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true)
      const data = await apiService.getHistory({ page: 1, page_size: 5 })
      setHistory(data)
    } catch {
      setHistory(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory, refreshTrigger])

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    try {
      await apiService.deleteHistoryRecord(id)
      fetchHistory()
    } catch {
      // ignore
    }
  }

  const records = history?.records || []

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(180deg, #8b5cf6, #c4b5fd)' }} />
          <h3 className="text-sm font-bold text-slate-200 tracking-wide">历史记录</h3>
        </div>
        {history && history.total > 0 && (
          <span className="text-[10px] text-slate-500">{history.total} 条</span>
        )}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-14 rounded-lg" />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="text-center py-8">
          <History className="w-8 h-8 text-slate-700 mx-auto mb-2" />
          <p className="text-xs text-slate-600">暂无生成记录</p>
        </div>
      ) : (
        <div className="space-y-2">
          {records.map((record) => (
            <div
              key={record.id}
              onClick={() => onSelectRecord(record)}
              className="flex items-center gap-3 p-2.5 rounded-lg cursor-pointer transition-all duration-200 group"
              style={{ background: 'rgba(10, 10, 15, 0.3)', border: '1px solid rgba(255, 255, 255, 0.04)' }}
            >
              {record.best_image_data ? (
                <img
                  src={`data:image/png;base64,${record.best_image_data}`}
                  alt="缩略图"
                  className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
                />
              ) : (
                <div className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'rgba(255,255,255,0.03)' }}>
                  <History className="w-4 h-4 text-slate-600" />
                </div>
              )}

              <div className="flex-1 min-w-0">
                <div className="text-xs text-slate-300 truncate font-medium">
                  {record.prompt}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {record.best_score != null && (
                    <span className="text-[10px] text-amber-400 font-semibold">
                      {record.best_score.toFixed(1)}分
                    </span>
                  )}
                  <span className="text-[10px] text-slate-600">
                    {record.backend}
                  </span>
                  {record.refinement_rounds > 0 && (
                    <span className="text-[10px] text-violet-400/60">
                      ↻{record.refinement_rounds}
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={(e) => handleDelete(e, record.id)}
                className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-rose-500/10"
              >
                <Trash2 className="w-3.5 h-3.5 text-slate-500 hover:text-rose-400" />
              </button>

              <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 transition-colors flex-shrink-0" />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
