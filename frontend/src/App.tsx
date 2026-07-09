import { useState, useEffect, useRef, useCallback } from 'react'
import { Sparkles, AlertCircle, Activity, Settings } from 'lucide-react'
import { GenerationForm } from '@/components/GenerationForm'
import { ImageGallery } from '@/components/ImageGallery'
import { ResultDetails } from '@/components/ResultDetails'
import { StatusBadge } from '@/components/StatusBadge'
import { HistoryPanel } from '@/components/HistoryPanel'
import { ApiKeySettings } from '@/components/ApiKeySettings'
import { apiService } from '@/services/api'
import type {
  GenerationRequest,
  GenerationResponse,
  GeneratedImage,
  HealthStatus,
  HistoryRecord,
  StreamEvent,
} from '@/types/api'
import '@/styles/index.css'

interface StepStatus {
  status: 'idle' | 'loading' | 'success' | 'error'
  text: string
  progress: number
}

const INITIAL_STEPS: Record<string, StepStatus> = {
  optimize_prompt: { status: 'idle', text: '优化提示词 (3变体)', progress: 0 },
  optimize_parameters: { status: 'idle', text: '智能调整参数', progress: 0 },
  generate_images: { status: 'idle', text: 'Ensemble 生图', progress: 0 },
  score_images: { status: 'idle', text: 'CLIP 批量评分', progress: 0 },
  evaluate_quality: { status: 'idle', text: '质量门控', progress: 0 },
  seed_refine: { status: 'idle', text: '变体搜索', progress: 0 },
  img2img_refine: { status: 'idle', text: 'img2img 精修', progress: 0 },
}

function App() {
  const [isLoading, setIsLoading] = useState(false)
  const [response, setResponse] = useState<GenerationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null)
  const [steps, setSteps] = useState<Record<string, StepStatus>>({ ...INITIAL_STEPS })
  const [historyRefresh, setHistoryRefresh] = useState(0)
  const [showApiSettings, setShowApiSettings] = useState(false)
  const cancelRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    apiService.checkHealth().then(setHealth).catch(() => setHealth(null))
  }, [])

  const handleEvent = useCallback((event: StreamEvent) => {
    setSteps((prev) => {
      const next = { ...prev }

      if (next[event.step]) {
        next[event.step] = {
          status: event.status === 'done' ? 'success' : event.status === 'error' ? 'error' : 'loading',
          text: event.message,
          progress: event.progress,
        }
      }

      const stepOrder = Object.keys(INITIAL_STEPS)
      const currentIdx = stepOrder.indexOf(event.step)
      if (currentIdx >= 0 && event.status === 'done') {
        const nextStep = stepOrder[currentIdx + 1]
        if (nextStep && next[nextStep]?.status === 'idle') {
          next[nextStep] = { ...next[nextStep], status: 'loading' }
        }
      }

      return next
    })
  }, [])

  const handleGenerate = useCallback((request: GenerationRequest) => {
    setIsLoading(true)
    setError(null)
    setResponse(null)
    setSelectedImage(null)
    setSteps({ ...INITIAL_STEPS })

    setSteps((prev) => ({
      ...prev,
      optimize_prompt: { ...prev.optimize_prompt, status: 'loading' },
    }))

    cancelRef.current = apiService.generateImageStream(
      request,
      handleEvent,
      (result) => {
        setResponse(result)
        setIsLoading(false)
        setHistoryRefresh((n) => n + 1)
      },
      (err) => {
        setError(err)
        setIsLoading(false)
      },
    )
  }, [handleEvent])

  const handleHistorySelect = useCallback((_record: HistoryRecord) => {
    // 将来可展开为加载历史详情
  }, [])

  useEffect(() => {
    return () => {
      cancelRef.current?.()
    }
  }, [])

  return (
    <div className="min-h-screen relative" style={{ background: '#0a0a0f' }}>
      {/* 背景极光动效 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute top-[-10%] left-[10%] w-[500px] h-[500px] rounded-full blur-[120px] animate-float"
          style={{ background: 'radial-gradient(circle, rgba(245, 158, 11, 0.08), transparent 70%)' }}
        />
        <div
          className="absolute top-[30%] right-[5%] w-[400px] h-[400px] rounded-full blur-[100px] animate-float"
          style={{ background: 'radial-gradient(circle, rgba(139, 92, 246, 0.06), transparent 70%)', animationDelay: '2s' }}
        />
        <div
          className="absolute bottom-[5%] left-[30%] w-[450px] h-[450px] rounded-full blur-[110px] animate-float"
          style={{ background: 'radial-gradient(circle, rgba(244, 63, 94, 0.05), transparent 70%)', animationDelay: '4s' }}
        />
      </div>

      <div className="relative z-10">
        {/* 头部 */}
        <header className="border-b border-white/[0.04] backdrop-blur-xl sticky top-0 z-40" style={{ background: 'rgba(10, 10, 15, 0.7)' }}>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="p-2.5 rounded-xl flex items-center justify-center"
                  style={{
                    background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(244, 63, 94, 0.2), rgba(139, 92, 246, 0.2))',
                    border: '1px solid rgba(245, 158, 11, 0.2)',
                  }}
                >
                  <Sparkles className="w-5 h-5" style={{ color: '#fbbf24' }} />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-slate-100 tracking-tight">
                    EasyDrawer
                  </h1>
                </div>
              </div>

              {health && (
                <div className="hidden md:flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <Activity className="w-3.5 h-3.5 text-teal-400" />
                    <span className="text-slate-400">API</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${health.api === 'healthy' ? 'bg-teal-400' : 'bg-red-400'}`} />
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <span className="text-slate-400">SD</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${health.stable_diffusion === 'healthy' ? 'bg-teal-400' : 'bg-amber-400'}`} />
                  </div>
                  <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <span className="text-slate-400">LLM</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${health.llm === 'configured' ? 'bg-teal-400' : 'bg-red-400'}`} />
                  </div>
                  <button
                    onClick={() => setShowApiSettings(true)}
                    className="p-2 hover:bg-white/5 rounded-lg transition-colors"
                    title="配置 API 密钥"
                  >
                    <Settings className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* 主内容 */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 左侧 */}
            <div className="lg:col-span-1 space-y-6">
              <GenerationForm
                onSubmit={handleGenerate}
                isLoading={isLoading}
                defaultBackend={health?.default_backend}
              />

              {isLoading && (
                <div className="card-glow space-y-3 animate-fade-up">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-slate-200 tracking-wide">生成进度</h3>
                    <span className="text-xs text-amber-400/60">实时</span>
                  </div>
                  {Object.entries(steps).map(([key, step]) => (
                    <StatusBadge
                      key={key}
                      status={step.status}
                      text={step.text}
                      progress={step.progress}
                    />
                  ))}
                  <div className="pt-3 mt-3 border-t border-white/5">
                    <p className="text-xs text-slate-500">
                      质量不达标时自动反馈优化
                    </p>
                  </div>
                </div>
              )}

              {error && (
                <div className="card animate-fade-up" style={{ borderColor: 'rgba(244, 63, 94, 0.2)' }}>
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-rose-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <h3 className="text-rose-300 font-semibold mb-1 text-sm">生成失败</h3>
                      <p className="text-xs text-rose-200/80 whitespace-pre-wrap">{error}</p>
                      {error.includes('ANTHROPIC_API_KEY') && (
                        <p className="text-xs text-rose-300/60 mt-2">
                          请在 .env 文件中配置 ANTHROPIC_API_KEY，然后重启后端。
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <HistoryPanel
                onSelectRecord={handleHistorySelect}
                refreshTrigger={historyRefresh}
              />
            </div>

            {/* 右侧 */}
            <div className="lg:col-span-2">
              {response ? (
                <div className="space-y-6 animate-fade-up">
                  <div className="card">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-bold text-slate-100">
                        生成结果
                      </h3>
                      <span className="badge-primary">
                        {response.images.length} 张
                      </span>
                    </div>
                    <ImageGallery
                      images={response.images}
                      bestImageSeed={response.best_image.seed}
                      onImageClick={(img) => setSelectedImage(img)}
                    />
                  </div>
                  <ResultDetails response={response} />
                </div>
              ) : (
                !isLoading && (
                  <div className="card h-full flex flex-col items-center justify-center py-20 text-center animate-scale-in">
                    <div
                      className="w-24 h-24 rounded-2xl flex items-center justify-center mb-6 relative"
                      style={{
                        background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(244, 63, 94, 0.08), rgba(139, 92, 246, 0.08))',
                        border: '1px solid rgba(245, 158, 11, 0.15)',
                      }}
                    >
                      <Sparkles className="w-10 h-10" style={{ color: '#fbbf24' }} />
                      <div
                        className="absolute inset-0 rounded-2xl animate-glow-pulse"
                        style={{ boxShadow: '0 0 40px rgba(245, 158, 11, 0.15)' }}
                      />
                    </div>
                    <h3 className="text-xl font-semibold text-slate-200 mb-2">
                      准备好创作了吗？
                    </h3>
                    <p className="text-slate-500 max-w-md text-sm leading-relaxed">
                      3 变体 Ensemble · CLIP 评分 · 反馈循环 · 变体搜索 · img2img 精修
                    </p>
                    <div className="mt-8 grid grid-cols-5 gap-3 text-sm max-w-lg">
                      {[
                        { value: '3x', label: 'Ensemble', color: '#fbbf24' },
                        { value: 'AI', label: 'CLIP 评分', color: '#c4b5fd' },
                        { value: '↻', label: '反馈循环', color: '#5eead4' },
                        { value: '◎', label: '变体搜索', color: '#fda4af' },
                        { value: '✦', label: 'img2img', color: '#f0abfc' },
                      ].map((item, idx) => (
                        <div key={idx} className="stat-card" style={{ color: item.color }}>
                          <div className="text-2xl font-bold" style={{ color: item.color }}>
                            {item.value}
                          </div>
                          <div className="text-[11px] text-slate-500 mt-1">{item.label}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        </main>
      </div>

      {/* 图片预览模态框 */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-scale-in"
          style={{ background: 'rgba(0, 0, 0, 0.92)', backdropFilter: 'blur(8px)' }}
          onClick={() => setSelectedImage(null)}
        >
          <div className="max-w-5xl w-full" onClick={(e) => e.stopPropagation()}>
            <img
              src={`data:image/png;base64,${selectedImage.image_data}`}
              alt="预览"
              className="w-full h-auto rounded-xl shadow-2xl"
            />
            <div className="mt-4 flex items-center justify-center gap-4 text-sm flex-wrap">
              <span className="text-amber-400 font-semibold">
                质量分 {selectedImage.quality_score?.toFixed(1)}
              </span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-400">种子 {selectedImage.seed}</span>
              {selectedImage.is_refined && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium" style={{ background: 'rgba(244, 63, 94, 0.15)', color: '#fda4af', border: '1px solid rgba(244, 63, 94, 0.25)' }}>
                  精修
                </span>
              )}
              {selectedImage.quality_breakdown && (
                <span className="text-slate-500 text-xs">
                  CLIP {selectedImage.quality_breakdown.clip_similarity.toFixed(0)} · 美学 {selectedImage.quality_breakdown.aesthetic_score.toFixed(0)} · 清晰度 {selectedImage.quality_breakdown.sharpness.toFixed(0)}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* API 密钥设置 */}
      {showApiSettings && <ApiKeySettings onClose={() => setShowApiSettings(false)} />}
    </div>
  )
}

export default App
