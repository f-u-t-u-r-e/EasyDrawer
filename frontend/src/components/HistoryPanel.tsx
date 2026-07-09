import React, { useState, useEffect, useCallback } from 'react'
import { Clock, Search, Trash2, Star, ChevronLeft, ChevronRight } from 'lucide-react'
import { apiService } from '@/services/api'
import type { HistoryRecord, HistoryListResponse } from '@/types/api'

interface HistoryPanelProps {
  onSelectRecord: (record: HistoryRecord) => void
  refreshTrigger?: number
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ onSelectRecord, refreshTrigger }) => {
  const [data, setData] = useState<HistoryListResponse | null>(null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const pageSize = 8

  const fetchHistory = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await apiService.getHistory({
        page,
        page_size: pageSize,
        search: search || undefined,
      })
      setData(result)
    } catch {
      // 历史服务不可用时静默失败
    } finally {
      setIsLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory, refreshTrigger])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await apiService.deleteHistoryRecord(id)
      fetchHistory()
    } catch {
      // 静默
    }
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
          <Clock className="w-5 h-5 text-blue-400" />
          生成历史
        </h3>
        {data && (
          <span className="text-xs text-slate-400">共 {data.total} 条</span>
        )}
      </div>

      {/* 搜索栏 */}
      <form onSubmit={handleSearch} className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="搜索提示词..."
            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </form>

      {/* 记录列表 */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-16 rounded-lg" />
          ))}
        </div>
      ) : data && data.records.length > 0 ? (
        <div className="space-y-2">
          {data.records.map((record) => (
            <div
              key={record.id}
              onClick={() => onSelectRecord(record)}
              className="flex items-center gap-3 p-3 bg-slate-900/30 rounded-lg border border-slate-700/50 hover:border-blue-500/50 cursor-pointer transition-all group"
            >
              {/* 缩略图 */}
              <img
                src={`data:image/png;base64,${record.best_image_data}`}
                alt=""
                className="w-12 h-12 rounded-md object-cover flex-shrink-0"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 truncate">{record.prompt}</p>
                <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
                  <span className="uppercase">{record.backend}</span>
                  <span>•</span>
                  {record.best_score != null && (
                    <>
                      <span className="flex items-center gap-0.5">
                        <Star className="w-3 h-3 text-yellow-400" />
                        {record.best_score.toFixed(0)}
                      </span>
                      <span>•</span>
                    </>
                  )}
                  <span>{record.generation_time.toFixed(1)}s</span>
                </div>
              </div>
              <button
                onClick={(e) => handleDelete(record.id, e)}
                className="p-1.5 text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-slate-500 text-sm">
          暂无历史记录
        </div>
      )}

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-700/50">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1.5 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-xs text-slate-400">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1.5 text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}
