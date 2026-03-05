import client from './client'

export interface EffectSummary {
  identifier: string
  display_name: string
  category: string
  description: string
}

export interface EffectDetail extends EffectSummary {
  parameter_schema: Record<string, unknown>
  preview_config: Record<string, unknown>
  reference_video_path: string
  sync_points: string[]
  quality_profiles: Record<string, Record<string, unknown>>
  initial_wait: number
}

export interface EffectCreateRequest {
  identifier: string
  display_name: string
  category: string
  description: string
  parameter_schema?: Record<string, unknown>
  preview_config?: Record<string, unknown>
  template_code?: string
  sync_points?: string[]
  quality_profiles?: Record<string, Record<string, unknown>>
}

export const listEffects = (category?: string) =>
  client.get<EffectSummary[]>('/effects', { params: category ? { category } : {} }).then(r => r.data)

export const getEffect = (identifier: string) =>
  client.get<EffectDetail>(`/effects/${identifier}`).then(r => r.data)

export const createEffect = (data: EffectCreateRequest) =>
  client.post<EffectDetail>('/effects', data).then(r => r.data)

export const getPreviewUrl = (identifier: string) =>
  `/api/effects/${identifier}/preview`

export const listAliases = () =>
  client.get<{ aliases: Record<string, string> }>('/effects/aliases').then(r => r.data.aliases)
