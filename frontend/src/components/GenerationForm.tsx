import React, { useState } from 'react'
import { Sparkles, Image as ImageIcon, Sliders, Zap } from 'lucide-react'
import type { GenerationRequest, ImageStyle, ImageBackend } from '@/types/api'

interface GenerationFormProps {
  onSubmit: (request: GenerationRequest) => void
  isLoading: boolean
  defaultBackend?: string
}

const STYLES: { value: ImageStyle; label: string; desc: string; icon: string }[] = [
  { value: 'realistic', label: '写实', desc: '照片级真实感', icon: '📷' },
  { value: 'artistic', label: '艺术', desc: '艺术概念风格', icon: '🎨' },
  { value: 'anime', label: '动漫', desc: '日系动漫风格', icon: '✨' },
  { value: 'portrait', label: '人像', desc: '专业人像摄影', icon: '👤' },
  { value: 'landscape', label: '风景', desc: '壮丽自然风光', icon: '🌄' },
  { value: 'concept_art', label: '概念艺术', desc: '游戏概念设计', icon: '🎮' },
]

const SIZES = [
  { label: '正方形 1:1', width: 1024, height: 1024 },
  { label: '横向 16:9', width: 1920, height: 1080 },
  { label: '竖向 9:16', width: 768, height: 1344 },
  { label: '人像 3:4', width: 768, height: 1024 },
]

const BACKENDS: { value: ImageBackend; label: string; desc: string }[] = [
  { value: 'sd', label: 'Stable Diffusion', desc: '开源生态，风格丰富' },
  { value: 'flux', label: 'FLUX', desc: '最强提示词遵循度' },
]

export const GenerationForm: React.FC<GenerationFormProps> = ({
  onSubmit,
  isLoading,
  defaultBackend = 'sd',
}) => {
  const [prompt, setPrompt] = useState('')
  const [style, setStyle] = useState<ImageStyle>('realistic')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [sizeIndex, setSizeIndex] = useState(0)
  const [backend, setBackend] = useState<ImageBackend>(defaultBackend as ImageBackend)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return

    const size = SIZES[sizeIndex]
    onSubmit({
      prompt: prompt.trim(),
      style,
      negative_prompt: negativePrompt.trim() || undefined,
      width: size.width,
      height: size.height,
      backend,
    })
  }

  const examplePrompts = [
    '一只可爱的橘猫坐在窗台上',
    '赛博朋克风格的未来城市夜景',
    '森林中的精灵女孩，光线穿过树叶',
    '雪山日出，金色阳光照耀山峰',
  ]

  return (
    <form onSubmit={handleSubmit} className="card space-y-5">
      <div className="flex items-center gap-2.5 mb-1">
        <div className="w-1 h-5 rounded-full" style={{ background: 'linear-gradient(180deg, #f59e0b, #f43f5e)' }} />
        <h2 className="text-lg font-bold text-slate-100 tracking-tight">创作你的图片</h2>
      </div>

      {/* 提示词输入 */}
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
          描述你想要的图片
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例如：一只可爱的橘猫坐在窗台上，阳光洒在它身上..."
          className="input-field h-28 resize-none text-sm"
          disabled={isLoading}
        />
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {examplePrompts.map((example, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setPrompt(example)}
              className="text-xs px-2.5 py-1 rounded-lg text-slate-400 hover:text-amber-300 transition-all duration-200"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}
              disabled={isLoading}
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* 生图后端选择 */}
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
          生图引擎
        </label>
        <div className="grid grid-cols-2 gap-2.5">
          {BACKENDS.map((b) => (
            <button
              key={b.value}
              type="button"
              onClick={() => setBackend(b.value)}
              disabled={isLoading}
              className={`backend-chip ${backend === b.value ? 'backend-chip-active' : ''}`}
            >
              <div className="flex items-center gap-2">
                <Zap className={`w-3.5 h-3.5 ${backend === b.value ? 'text-amber-400' : 'text-slate-500'}`} />
                <span className="font-semibold text-slate-200 text-sm">{b.label}</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">{b.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 风格选择 */}
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2.5 tracking-wide uppercase">
          选择风格
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
          {STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setStyle(s.value)}
              disabled={isLoading}
              className={`style-chip ${style === s.value ? 'style-chip-active' : ''}`}
            >
              <div className="font-semibold text-slate-200 text-sm">
                {s.icon} {s.label}
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">{s.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 尺寸选择 */}
      <div>
        <label className="block text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
          图片尺寸
        </label>
        <select
          value={sizeIndex}
          onChange={(e) => setSizeIndex(Number(e.target.value))}
          className="select-field text-sm"
          disabled={isLoading}
        >
          {SIZES.map((size, idx) => (
            <option key={idx} value={idx}>
              {size.label} — {size.width}×{size.height}
            </option>
          ))}
        </select>
      </div>

      {/* 高级设置 */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span className="tracking-wide">高级设置</span>
        </button>
        {showAdvanced && (
          <div className="mt-3 space-y-3 animate-fade-up">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2 tracking-wide uppercase">
                负面提示词
              </label>
              <textarea
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="例如：丑陋、模糊、低质量..."
                className="input-field h-16 resize-none text-sm"
                disabled={isLoading}
              />
            </div>
          </div>
        )}
      </div>

      {/* 提交按钮 */}
      <button
        type="submit"
        disabled={isLoading || !prompt.trim()}
        className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white" />
            <span>正在生成魔法中...</span>
          </>
        ) : (
          <>
            <ImageIcon className="w-4 h-4" />
            <span>开始生成</span>
            <Sparkles className="w-3.5 h-3.5 opacity-70" />
          </>
        )}
      </button>
    </form>
  )
}
