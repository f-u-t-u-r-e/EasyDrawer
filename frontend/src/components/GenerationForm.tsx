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
  { label: '正方形 (1:1)', width: 1024, height: 1024 },
  { label: '横向 (16:9)', width: 1920, height: 1080 },
  { label: '竖向 (9:16)', width: 768, height: 1344 },
  { label: '人像 (3:4)', width: 768, height: 1024 },
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
    <form onSubmit={handleSubmit} className="card space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <Sparkles className="w-6 h-6 text-blue-400" />
        <h2 className="text-2xl font-bold text-slate-100">创作你的图片</h2>
      </div>

      {/* 提示词输入 */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          描述你想要的图片
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例如：一只可爱的橘猫坐在窗台上，阳光洒在它身上..."
          className="input-field h-32 resize-none"
          disabled={isLoading}
        />
        <div className="mt-2 flex flex-wrap gap-2">
          {examplePrompts.map((example, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setPrompt(example)}
              className="text-xs px-3 py-1 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-full transition-colors"
              disabled={isLoading}
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      {/* 生图后端选择 */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          生图引擎
        </label>
        <div className="grid grid-cols-2 gap-3">
          {BACKENDS.map((b) => (
            <button
              key={b.value}
              type="button"
              onClick={() => setBackend(b.value)}
              disabled={isLoading}
              className={`p-3 rounded-lg border-2 transition-all text-left ${
                backend === b.value
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-700 bg-slate-900/30 hover:border-slate-600'
              }`}
            >
              <div className="flex items-center gap-2">
                <Zap className={`w-4 h-4 ${backend === b.value ? 'text-blue-400' : 'text-slate-500'}`} />
                <span className="font-semibold text-slate-200">{b.label}</span>
              </div>
              <div className="text-xs text-slate-400 mt-1">{b.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 风格选择 */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-3">选择风格</label>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {STYLES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setStyle(s.value)}
              disabled={isLoading}
              className={`p-4 rounded-lg border-2 transition-all text-left ${
                style === s.value
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-700 bg-slate-900/30 hover:border-slate-600'
              }`}
            >
              <div className="font-semibold text-slate-200">
                {s.icon} {s.label}
              </div>
              <div className="text-xs text-slate-400 mt-1">{s.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 尺寸选择 */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">图片尺寸</label>
        <select
          value={sizeIndex}
          onChange={(e) => setSizeIndex(Number(e.target.value))}
          className="select-field"
          disabled={isLoading}
        >
          {SIZES.map((size, idx) => (
            <option key={idx} value={idx}>
              {size.label} - {size.width}×{size.height}
            </option>
          ))}
        </select>
      </div>

      {/* 高级设置 */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-300 transition-colors"
        >
          <Sliders className="w-4 h-4" />
          <span>高级设置</span>
        </button>
        {showAdvanced && (
          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                负面提示词（要排除的内容）
              </label>
              <textarea
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="例如：丑陋、模糊、低质量..."
                className="input-field h-20 resize-none"
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
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
            <span>正在生成魔法中...</span>
          </>
        ) : (
          <>
            <ImageIcon className="w-5 h-5" />
            <span>开始生成</span>
          </>
        )}
      </button>
    </form>
  )
}
