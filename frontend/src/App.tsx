import React, { useState, useEffect, useRef, useCallback } from 'react'
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
  optimize_prompt: { status: 'idle', text: '优化提示词 (3变体)...', progress: 0 },
  optimize_parameters: { status: 'idle', text: '智能调整参数...', progress: 0 },
  generate_images: { status: 'idle', text: 'Ensemble 生图...', progress: 0 },
  score_images: { status: 'idle', text: '批量质量评估...', progress: 0 },
  evaluate_quality: { status: 'idle', text: '评估是否需要优化...', progress: 0 },
  seed_refine: { status: 'idle', text: 'Seed 邻域精搜...', progress: 0 },
  img2img_refine: { status: 'idle', text: 'img2img 精修...', progress: 0 },
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

      // 标记下一步为 loading
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-slow" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />
      </div>

      <div className="relative z-10">
        {/* 头部 */}
        <header className="border-b border-slate-700/50 backdrop-blur-sm bg-slate-900/50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-100">EasyDrawer</h1>
                </div>
              </div>

              {health && (
                <div className="hidden md:flex items-center gap-4 text-xs">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-green-400" />
                    <span className="text-slate-300">API</span>
                    <span className={`w-2 h-2 rounded-full ${health.api === 'healthy' ? 'bg-green-400' : 'bg-red-400'}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-300">SD</span>
                    <span className={`w-2 h-2 rounded-full ${health.stable_diffusion === 'healthy' ? 'bg-green-400' : 'bg-yellow-400'}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-300">FLUX</span>
                    <span className={`w-2 h-2 rounded-full ${health.flux === 'configured' ? 'bg-green-400' : 'bg-slate-600'}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-300">LLM</span>
                    <span className={`w-2 h-2 rounded-full ${health.llm === 'configured' ? 'bg-green-400' : 'bg-red-400'}`} />
                    {health.llm === 'not_configured' && (
                      <span className="text-yellow-400 text-[10px]">未配置</span>
                    )}
                  </div>
                  <button
                    onClick={() => setShowApiSettings(true)}
                    className="ml-2 p-1.5 hover:bg-slate-700/50 rounded-lg transition-colors"
                    title="配置 API 密钥"
                  >
                    <Settings className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* 主内容 — 3 列布局 */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* 左侧：生成表单 + 进度 + 历史 */}
            <div className="lg:col-span-1">
              <GenerationForm
                onSubmit={handleGenerate}
                isLoading={isLoading}
                defaultBackend={health?.default_backend}
              />

              {/* 实时流程状态 */}
              {isLoading && (
                <div className="card mt-6 space-y-3">
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">生成进度</h3>
                  {Object.entries(steps).map(([key, step]) => (
                    <StatusBadge
                      key={key}
                      status={step.status}
                      text={step.text}
                      progress={step.progress}
                    />
                  ))}
                  <div className="pt-4 border-t border-slate-700">
                    <p className="text-sm text-slate-400">
                      质量不达标会自动优化重试 ✨
                    </p>
                  </div>
                </div>
              )}

              {error && (
                <div className="card mt-6 bg-red-500/10 border-red-500/30">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <h3 className="text-red-300 font-semibold mb-1">生成失败</h3>
                      <p className="text-sm text-red-200 whitespace-pre-wrap">{error}</p>
                      {error.includes('ANTHROPIC_API_KEY') && (
                        <p className="text-xs text-red-300 mt-2">
                          请在项目根目录的 .env 文件中配置 ANTHROPIC_API_KEY，然后重启后端服务。
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* 历史记录面板 */}
              <div className="mt-6">
                <HistoryPanel
                  onSelectRecord={handleHistorySelect}
                  refreshTrigger={historyRefresh}
                />
              </div>
            </div>

            {/* 右侧：结果展示（占 2 列） */}
            <div className="lg:col-span-2">
              {response ? (
                <div className="space-y-6">
                  <div className="card">
                    <h3 className="text-xl font-bold text-slate-100 mb-4">
                      生成结果 ({response.images.length}张)
                    </h3>
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
                  <div className="card h-full flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-20 h-20 bg-gradient-to-br from-blue-500/20 to-purple-600/20 rounded-full flex items-center justify-center mb-4">
                      <Sparkles className="w-10 h-10 text-blue-400" />
                    </div>
                    <h3 className="text-xl font-semibold text-slate-300 mb-2">
                      准备好创作了吗？
                    </h3>
                    <p className="text-slate-400 max-w-md">
                      3 变体 Ensemble → 批量评分 → 反馈循环 → Seed 精搜 → img2img 精修
                    </p>
                    <div className="mt-6 grid grid-cols-5 gap-4 text-sm">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-400">3x</div>
                        <div className="text-slate-400 mt-1">变体 Ensemble</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-400">AI</div>
                        <div className="text-slate-400 mt-1">CLIP 评分</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">🔄</div>
                        <div className="text-slate-400 mt-1">反馈循环</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-yellow-400">🎯</div>
                        <div className="text-slate-400 mt-1">Seed 精搜</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-pink-400">✨</div>
                        <div className="text-slate-400 mt-1">img2img</div>
                      </div>
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
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="max-w-5xl w-full">
            <img
              src={`data:image/png;base64,${selectedImage.image_data}`}
              alt="预览"
              className="w-full h-auto rounded-lg shadow-2xl"
            />
            <div className="mt-4 text-center text-slate-300 text-sm">
              质量分: {selectedImage.quality_score?.toFixed(1)} | 种子: {selectedImage.seed}
              {selectedImage.is_refined && (
                <span className="ml-2 px-2 py-0.5 bg-pink-500/20 text-pink-300 rounded-full text-xs">
                  精修
                </span>
              )}
              {selectedImage.quality_breakdown && (
                <span className="ml-4 text-slate-400">
                  CLIP: {selectedImage.quality_breakdown.clip_similarity.toFixed(0)} |
                  美学: {selectedImage.quality_breakdown.aesthetic_score.toFixed(0)} |
                  清晰度: {selectedImage.quality_breakdown.sharpness.toFixed(0)}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* API 密钥设置模态框 */}
      {showApiSettings && <ApiKeySettings onClose={() => setShowApiSettings(false)} />}
    </div>
  )
}

export default App
