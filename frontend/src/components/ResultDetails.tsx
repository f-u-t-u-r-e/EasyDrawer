import { useState } from 'react'
import { Copy, Check, ChevronDown, ChevronUp } from 'lucide-react'
import type { GenerationResponse } from '@/types/api'

interface ResultDetailsProps {
  response: GenerationResponse
}

export const ResultDetails: React.FC<ResultDetailsProps> = ({ response }) => {
  const [copied, setCopied] = useState<string | null>(null)
  const [showPrompt, setShowPrompt] = useState(false)

  const best = response.best_image
  const breakdown = best.quality_breakdown

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopied(label)
    setTimeout(() => setCopied(null), 2000)
  }

  const qualityMetrics = breakdown
    ? [
        { label: 'CLIP 相似度', value: breakdown.clip_similarity, color: '#fbbf24', desc: '图文匹配度' },
        { label: '美学评分', value: breakdown.aesthetic_score, color: '#c4b5fd', desc: '画面美感' },
        { label: '技术质量', value: breakdown.technical_score, color: '#5eead4', desc: '分辨率+对比度' },
        { label: '清晰度', value: breakdown.sharpness, color: '#fda4af', desc: '拉普拉斯方差' },
      ]
    : []

  return (
    <div className="space-y-6">
      {/* 统计概览 */}
      <div className="card">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="stat-card" style={{ color: '#fbbf24' }}>
            <div className="text-2xl font-bold" style={{ color: '#fbbf24' }}>
              {best.quality_score?.toFixed(1)}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">最终质量分</div>
          </div>
          <div className="stat-card" style={{ color: '#5eead4' }}>
            <div className="text-2xl font-bold" style={{ color: '#5eead4' }}>
              {response.images.length}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">生成图片数</div>
          </div>
          <div className="stat-card" style={{ color: '#c4b5fd' }}>
            <div className="text-2xl font-bold" style={{ color: '#c4b5fd' }}>
              {response.generation_time.toFixed(1)}s
            </div>
            <div className="text-[11px] text-slate-500 mt-1">总耗时</div>
          </div>
          <div className="stat-card" style={{ color: '#fda4af' }}>
            <div className="text-2xl font-bold" style={{ color: '#fda4af' }}>
              {response.refinement_rounds}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">反馈轮次</div>
          </div>
        </div>
      </div>

      {/* 质量分解 */}
      {breakdown && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(180deg, #f59e0b, #14b8a6)' }} />
            <h3 className="text-sm font-bold text-slate-200 tracking-wide">质量分解</h3>
            {breakdown.scoring_mode && breakdown.scoring_mode !== 'full' && (
              <span className="text-[10px] px-2 py-0.5 rounded-full text-amber-300" style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                {breakdown.scoring_mode === 'technical_only' ? '仅技术模式' : breakdown.scoring_mode}
              </span>
            )}
          </div>
          <div className="space-y-3.5">
            {qualityMetrics.map((metric) => (
              <div key={metric.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-300">{metric.label}</span>
                    <span className="text-[10px] text-slate-600">{metric.desc}</span>
                  </div>
                  <span className="text-sm font-semibold" style={{ color: metric.color }}>
                    {metric.value.toFixed(1)}
                  </span>
                </div>
                <div className="quality-bar">
                  <div
                    className="quality-bar-fill"
                    style={{
                      width: `${metric.value}%`,
                      background: `linear-gradient(90deg, ${metric.color}80, ${metric.color})`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
            <span className="text-xs text-slate-500">综合加权分</span>
            <span className="text-lg font-bold text-amber-400">{breakdown.overall.toFixed(1)}</span>
          </div>
        </div>
      )}

      {/* 提示词详情 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(180deg, #8b5cf6, #f43f5e)' }} />
          <h3 className="text-sm font-bold text-slate-200 tracking-wide">提示词优化</h3>
        </div>

        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-slate-500 uppercase tracking-wide">原始提示词</span>
            </div>
            <div
              className="text-sm text-slate-400 p-2.5 rounded-lg"
              style={{ background: 'rgba(10, 10, 15, 0.4)', border: '1px solid rgba(255, 255, 255, 0.04)' }}
            >
              {response.optimized_prompt.original}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-slate-500 uppercase tracking-wide">优化后（主提示词）</span>
              <button
                onClick={() => copyToClipboard(response.optimized_prompt.enhanced, 'enhanced')}
                className="text-xs text-slate-500 hover:text-amber-300 transition-colors flex items-center gap-1"
              >
                {copied === 'enhanced' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied === 'enhanced' ? '已复制' : '复制'}
              </button>
            </div>
            <div
              className="text-sm text-slate-200 p-2.5 rounded-lg leading-relaxed"
              style={{ background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.1)' }}
            >
              {response.optimized_prompt.enhanced}
            </div>
          </div>

          {response.optimized_prompt.variants && response.optimized_prompt.variants.length > 0 && (
            <div>
              <button
                onClick={() => setShowPrompt(!showPrompt)}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showPrompt ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                <span>查看 {response.optimized_prompt.variants.length} 个变体</span>
              </button>
              {showPrompt && (
                <div className="mt-2.5 space-y-2 animate-fade-up">
                  {response.optimized_prompt.variants.map((variant, idx) => (
                    <div
                      key={idx}
                      className="text-xs text-slate-400 p-2.5 rounded-lg"
                      style={{ background: 'rgba(10, 10, 15, 0.3)', border: '1px solid rgba(255, 255, 255, 0.04)' }}
                    >
                      <span className="text-amber-400/60 font-medium mr-2">变体 {idx + 1}</span>
                      {variant.enhanced}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] text-slate-500 uppercase tracking-wide">负面提示词</span>
              <button
                onClick={() => copyToClipboard(response.optimized_prompt.negative, 'negative')}
                className="text-xs text-slate-500 hover:text-amber-300 transition-colors flex items-center gap-1"
              >
                {copied === 'negative' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied === 'negative' ? '已复制' : '复制'}
              </button>
            </div>
            <div
              className="text-xs text-slate-400 p-2.5 rounded-lg leading-relaxed"
              style={{ background: 'rgba(244, 63, 94, 0.04)', border: '1px solid rgba(244, 63, 94, 0.08)' }}
            >
              {response.optimized_prompt.negative}
            </div>
          </div>
        </div>
      </div>

      {/* 生成参数 */}
      {best.parameters && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1 h-4 rounded-full" style={{ background: 'linear-gradient(180deg, #14b8a6, #5eead4)' }} />
            <h3 className="text-sm font-bold text-slate-200 tracking-wide">生成参数</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {Object.entries(best.parameters).filter(([k]) => k !== 'prompt' && k !== 'negative_prompt').map(([key, value]) => (
              <div key={key} className="p-2.5 rounded-lg" style={{ background: 'rgba(10, 10, 15, 0.3)', border: '1px solid rgba(255, 255, 255, 0.04)' }}>
                <div className="text-[10px] text-slate-600 uppercase tracking-wide">{key}</div>
                <div className="text-slate-300 font-mono text-xs mt-0.5">
                  {typeof value === 'number' ? value : String(value)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
