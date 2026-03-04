// TypeScript interfaces matching Pydantic models

export type ProjectStatus = 'DRAFT' | 'IN_PROGRESS' | 'REVIEW' | 'RENDERED' | 'PUBLISHED'
export type PipelineStage = 'RESEARCH' | 'TOPIC' | 'SCRIPT' | 'AUDIO' | 'VISUAL' | 'RENDER'
export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'
export type TopicStatus = 'PENDING' | 'SELECTED' | 'REJECTED'

export interface Project {
  id: string
  title: string
  description: string
  status: ProjectStatus
  current_stage: PipelineStage
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  title: string
  description?: string
}

export interface ProjectUpdate {
  title?: string
  description?: string
  status?: ProjectStatus
  current_stage?: PipelineStage
}

export interface Job {
  id: string
  project_id: string
  job_type: string
  status: JobStatus
  input_json?: unknown
  output_json?: unknown
  error?: string
  created_at: string
  updated_at: string
}

export interface Topic {
  id: string
  project_id: string
  title: string
  source: string
  score: number
  keywords: string[]
  status: TopicStatus
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TopicCreate {
  title: string
  source?: string
  score?: number
  keywords?: string[]
  metadata?: Record<string, unknown>
}

export interface TopicUpdate {
  title?: string
  status?: TopicStatus
}

export interface ScriptVersion {
  id: number
  project_id: string
  topic_id: string
  version: number
  title: string
  script_json: Record<string, unknown>
  is_finalized: boolean
  created_at: string
}

export interface ScriptVersionCreate {
  topic_id: string
  title: string
  script_json: Record<string, unknown>
}

export interface ScriptVersionUpdate {
  title?: string
  script_json?: Record<string, unknown>
}

export interface DiffResult {
  version_a: number
  version_b: number
  changes: Array<{ type: string; content: string }>
}

export interface VoiceParams {
  speed: number
  temperature: number
  top_p: number
  repetition_penalty: number
  emotion: string
  emphasis: string
}

export interface AudioSegment {
  id: number
  project_id: string
  script_version_id: number
  scene_number: number
  start_time: string
  end_time: string
  narration_text: string
  voice_params?: VoiceParams
  audio_file_path?: string
  status: string
  version: number
  created_at: string
}

export interface AudioTimeline {
  segments: AudioSegment[]
  total_duration: string
  segment_count: number
}

export interface Scene {
  id: number
  project_id: string
  scene_number: number
  visual_type: string
  visual_data: Record<string, unknown>
  stock_video_path?: string
  rendered_path?: string
  thumbnail_path?: string
  transition: string
  effects: string[]
  show_title: boolean
  target_duration: number | null
  clip_count: number
  duration: number | null
  status: string
  created_at: string
  updated_at: string
}

export interface FootageResult {
  video_id: number
  url: string
  preview_url: string
  duration: number
  width: number
  height: number
}

export interface WikimediaImageResult {
  title: string
  url: string
  thumb_url: string
  width: number
  height: number
  license: string
  attribution: string
}

export interface PixabayVideoResult {
  video_id: number
  url: string
  preview_url: string
  duration: number
  width: number
  height: number
  tags: string
}

export interface UnsplashPhotoResult {
  photo_id: string
  url: string
  thumb_url: string
  page_url: string
  width: number
  height: number
  description: string
  photographer: string
}

export interface MusicSettings {
  volume: number
  fade_in_ms: number
  fade_out_ms: number
}

export interface WebSocketMessage {
  event: 'job_started' | 'job_progress' | 'job_completed' | 'job_failed'
  job_id: string
  job_type: string
  data: Record<string, unknown>
}


// Keyword Suggestion Tool types
export interface KeywordSuggestion {
  keyword: string
  rank: number
  original_term: string | null
  visual_synonym: string | null
  category: string | null
  source_hints: Record<string, string> | null
}

export interface NarrativeBeat {
  beat: string
  timestamp_hint: string | null
  suggested_keywords: string[]
}

export interface SuggestKeywordsResponse {
  suggestions: KeywordSuggestion[]
  aesthetic_hints: string[]
  keyword_categories: Record<string, string[]>
  narrative_beats: NarrativeBeat[]
}
