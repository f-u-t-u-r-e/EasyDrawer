export interface GenerationRequest {
  prompt: string
  style?: ImageStyle
  negative_prompt?: string
  width?: number
  height?: number
  session_id?: string
  backend?: ImageBackend
}

export type ImageStyle =
  | 'realistic'
  | 'artistic'
  | 'anime'
  | 'concept_art'
  | 'portrait'
  | 'landscape'

export type SceneType =
  | 'portrait'
  | 'landscape'
  | 'product'
  | 'artistic'
  | 'architecture'

export type ImageBackend = 'sd' | 'flux'

export interface PromptVariant {
  enhanced: string
  negative: string
  focus: string
}

export interface OptimizedPrompt {
  original: string
  enhanced: string
  negative: string
  scene_type: SceneType
  style: ImageStyle
  reasoning: string
  variants: PromptVariant[]
}

export interface SDParameters {
  prompt: string
  negative_prompt: string
  steps: number
  cfg_scale: number
  width: number
  height: number
  sampler_name: string
  seed: number
  init_image?: string | null
  denoising_strength?: number | null
}

export interface FLUXParameters {
  prompt: string
  width: number
  height: number
  steps: number
  guidance: number
  seed: number
}

export interface QualityBreakdown {
  clip_similarity: number
  aesthetic_score: number
  technical_score: number
  sharpness: number
  overall: number
}

export interface GeneratedImage {
  image_data: string
  seed: number
  quality_score?: number
  quality_breakdown?: QualityBreakdown
  parameters: SDParameters | FLUXParameters
  variant_index: number
  is_refined: boolean
}

export interface GenerationResponse {
  session_id: string
  optimized_prompt: OptimizedPrompt
  images: GeneratedImage[]
  best_image: GeneratedImage
  generation_time: number
  refinement_rounds: number
  backend_used: string
}

export interface HealthStatus {
  api: string
  stable_diffusion: string
  flux: string
  llm: string
  llm_warning?: string | null
  default_backend: string
  quality_threshold: number
  max_refinement_rounds: number
}

export interface StreamEvent {
  step: string
  status: 'running' | 'done' | 'error'
  message: string
  progress: number
  data?: GenerationResponse
}

// ── 历史记录 ─────────────────────────────────────────────

export interface HistoryRecord {
  id: string
  created_at: string
  prompt: string
  style: string | null
  backend: string
  best_score: number | null
  image_count: number
  generation_time: number
  refinement_rounds: number
  best_image_data: string
  best_seed: number
  optimized_prompt_text: string
  quality_breakdown: QualityBreakdown | null
}

export interface HistoryListResponse {
  records: HistoryRecord[]
  total: number
  page: number
  page_size: number
}
