import axios from 'axios'
import type {
  GenerationRequest,
  GenerationResponse,
  OptimizedPrompt,
  HealthStatus,
  StreamEvent,
  HistoryListResponse,
  HistoryRecord,
} from '@/types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
  headers: { 'Content-Type': 'application/json' },
})

// 动态配置 LLM
interface LLMConfig {
  provider: string
  apiKey: string
  baseUrl: string
  model: string
}

let runtimeLLMConfig: LLMConfig | null = null

export function setLLMConfig(config: LLMConfig | null) {
  runtimeLLMConfig = config
  if (config) {
    localStorage.setItem('llm_config', JSON.stringify(config))
  } else {
    localStorage.removeItem('llm_config')
  }
}

export function getLLMConfig(): LLMConfig | null {
  if (runtimeLLMConfig) return runtimeLLMConfig
  const saved = localStorage.getItem('llm_config')
  if (saved) {
    runtimeLLMConfig = JSON.parse(saved)
  }
  return runtimeLLMConfig
}

// 兼容旧接口
export function setApiKey(key: string | null) {
  if (key && runtimeLLMConfig) {
    runtimeLLMConfig.apiKey = key
    setLLMConfig(runtimeLLMConfig)
  }
}

export function getApiKey(): string | null {
  return runtimeLLMConfig?.apiKey || null
}

api.interceptors.request.use((config) => {
  const llmConfig = getLLMConfig()
  if (llmConfig?.apiKey) {
    config.headers['X-LLM-API-Key'] = llmConfig.apiKey
    config.headers['X-Anthropic-API-Key'] = llmConfig.apiKey
    config.headers['X-LLM-Provider'] = llmConfig.provider
    config.headers['X-LLM-Base-URL'] = llmConfig.baseUrl
    config.headers['X-LLM-Model'] = llmConfig.model
  }
  return config
})

export const apiService = {
  async checkHealth(): Promise<HealthStatus> {
    const { data } = await api.get<HealthStatus>('/health')
    return data
  },

  async generateImage(request: GenerationRequest): Promise<GenerationResponse> {
    const { data } = await api.post<GenerationResponse>('/generate', request)
    return data
  },

  /**
   * 流式生成图片 — 通过 SSE 接收实时进度
   */
  generateImageStream(
    request: GenerationRequest,
    onEvent: (event: StreamEvent) => void,
    onComplete: (response: GenerationResponse) => void,
    onError: (error: string) => void,
  ): () => void {
    const controller = new AbortController()

    ;(async () => {
      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        }

        // 添加 LLM 配置 headers
        const llmConfig = getLLMConfig()
        if (llmConfig?.apiKey) {
          headers['X-LLM-API-Key'] = llmConfig.apiKey
          headers['X-Anthropic-API-Key'] = llmConfig.apiKey
          headers['X-LLM-Provider'] = llmConfig.provider
          headers['X-LLM-Base-URL'] = llmConfig.baseUrl
          headers['X-LLM-Model'] = llmConfig.model
        }

        const response = await fetch('/api/generate/stream', {
          method: 'POST',
          headers,
          body: JSON.stringify(request),
          signal: controller.signal,
        })

        if (!response.ok) {
          // 尝试解析错误详情
          try {
            const errorData = await response.json()
            onError(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
          } catch {
            onError(`HTTP ${response.status}: ${response.statusText}`)
          }
          return
        }

        const reader = response.body?.getReader()
        if (!reader) {
          onError('浏览器不支持流式读取')
          return
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event: StreamEvent = JSON.parse(line.slice(6))
                onEvent(event)

                if (event.step === 'complete' && event.data) {
                  onComplete(event.data)
                }
                if (event.status === 'error') {
                  onError(event.message)
                }
              } catch {
                // 忽略非 JSON 行
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== 'AbortError') {
          onError(err.message || '流式连接失败')
        }
      }
    })()

    return () => controller.abort()
  },

  async optimizePrompt(prompt: string, style?: string): Promise<OptimizedPrompt> {
    const { data } = await api.post<OptimizedPrompt>('/optimize-prompt', null, {
      params: { prompt, style },
    })
    return data
  },

  // ── 历史记录 API ─────────────────────────────────────────

  async getHistory(params?: {
    page?: number
    page_size?: number
    search?: string
    backend?: string
  }): Promise<HistoryListResponse> {
    const { data } = await api.get<HistoryListResponse>('/history', { params })
    return data
  },

  async getHistoryRecord(id: string): Promise<HistoryRecord> {
    const { data } = await api.get<HistoryRecord>(`/history/${id}`)
    return data
  },

  async deleteHistoryRecord(id: string): Promise<void> {
    await api.delete(`/history/${id}`)
  },
}

export default api
