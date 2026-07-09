import React from 'react'
import { Lightbulb, Palette, Star, BarChart3, RefreshCw, Zap, Layers, Wand2 } from 'lucide-react'
import type { GenerationResponse } from '@/types/api'

interface ResultDetailsProps {
  response: GenerationResponse
}

const VARIANT_LABELS = ['构图', '光影', '细节']

export const ResultDetails: React.FC<ResultDetailsProps> = ({ response }) => {
  const { optimized_prompt, generation_time, images, best_image, refinement_rounds, backend_used } = response

  const breakdown = best_image.quality_breakdown
  const variants = optimized_prompt.variants || []
  const refinedCount = images.filter((i) => i.is_refined).length

  return (
    <div className="card space-y-6">
      <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
        <Star className="w-5 h-5 text-yellow-400" />
        生成详情
      </h3>

      {/* 提示词优化 */}
      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <Lightbulb className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="text-sm font-medium text-slate-300">优化思路</div>
            <p className="text-sm text-slate-400 bg-slate-900/50 rounded-lg p-3">
              {optimized_prompt.reasoning}
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Palette className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-300">
              <span>场景: {optimized_prompt.scene_type} | 风格: {optimized_prompt.style}</span>
              <span className="badge-primary flex items-center gap-1">
                <Zap className="w-3 h-3" />
                {backend_used.toUpperCase()}
              </span>
            </div>
            <details className="text-sm">
              <summary className="cursor-pointer text-slate-400 hover:text-slate-300 transition-colors">
                查看优化后的提示词
              </summary>
              <div className="mt-2 p-3 bg-slate-900/50 rounded-lg">
                <div className="text-green-400 mb-2">✓ 正面提示词:</div>
                <p className="text-slate-400 text-xs mb-3 break-all">{optimized_prompt.enhanced}</p>
                <div className="text-red-400 mb-2">✗ 负面提示词:</div>
                <p className="text-slate-400 text-xs break-all">{optimized_prompt.negative}</p>
              </div>
            </details>
          </div>
        </div>
      </div>

      {/* Ensemble 变体展示 */}
      {variants.length > 1 && (
        <div className="space-y-3 pt-4 border-t border-slate-700">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <Layers className="w-4 h-4 text-blue-400" />
            Ensemble 变体 ({variants.length}个)
          </div>
          <div className="grid grid-cols-1 gap-2">
            {variants.map((variant, idx) => (
              <details key={idx} className="text-sm">
                <summary className="cursor-pointer text-slate-400 hover:text-slate-300 transition-colors">
                  <span className="inline-block px-1.5 py-0.5 bg-blue-500/20 text-blue-300 text-[10px] rounded mr-2">
                    {VARIANT_LABELS[idx] || `变体${idx + 1}`}
                  </span>
                  {variant.focus}
                </summary>
                <div className="mt-1 ml-4 p-2 bg-slate-900/30 rounded text-xs text-slate-400 break-all">
                  {variant.enhanced}
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      {/* 质量分解 */}
      {breakdown && (
        <div className="space-y-3 pt-4 border-t border-slate-700">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            质量分解（最佳图片）
            {best_image.is_refined && (
              <span className="px-1.5 py-0.5 bg-pink-500/20 text-pink-300 text-[10px] rounded flex items-center gap-0.5">
                <Wand2 className="w-2.5 h-2.5" />
                精修
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'CLIP匹配度', value: breakdown.clip_similarity, color: 'blue' },
              { label: '美学评分', value: breakdown.aesthetic_score, color: 'purple' },
              { label: '技术质量', value: breakdown.technical_score, color: 'green' },
              { label: '清晰度', value: breakdown.sharpness, color: 'yellow' },
            ].map((item) => (
              <div key={item.label} className="bg-slate-900/50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-400">{item.label}</span>
                  <span className={`text-sm font-bold text-${item.color}-400`}>
                    {item.value.toFixed(0)}
                  </span>
                </div>
                <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-${item.color}-500 rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(100, item.value)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 生成统计 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 pt-4 border-t border-slate-700">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{images.length}</div>
          <div className="text-xs text-slate-400 mt-1">候选图片</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-400">
            {best_image.quality_score?.toFixed(0) || 'N/A'}
          </div>
          <div className="text-xs text-slate-400 mt-1">最高质量分</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-400">
            {generation_time.toFixed(1)}s
          </div>
          <div className="text-xs text-slate-400 mt-1">生成耗时</div>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1">
            <RefreshCw className="w-4 h-4 text-yellow-400" />
            <span className="text-2xl font-bold text-yellow-400">
              {refinement_rounds + 1}
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-1">优化轮次</div>
        </div>
        <div className="text-center">
          <div className="flex items-center justify-center gap-1">
            <Wand2 className="w-4 h-4 text-pink-400" />
            <span className="text-2xl font-bold text-pink-400">
              {refinedCount}
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-1">精修图片</div>
        </div>
      </div>
    </div>
  )
}
