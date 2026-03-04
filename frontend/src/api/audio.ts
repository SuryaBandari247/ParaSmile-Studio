import client from './client'
import type { AudioTimeline, AudioSegment } from '@/types'

export const generateTimeline = (projectId: string, scriptVersionId: number) =>
  client.post<AudioTimeline>(`/projects/${projectId}/audio/timeline`, { script_version_id: scriptVersionId }).then(r => r.data)

export const listSegments = (projectId: string) =>
  client.get<AudioSegment[]>(`/projects/${projectId}/audio/segments`).then(r => r.data)

export const updateSegment = (projectId: string, segmentId: number, data: Partial<AudioSegment>) =>
  client.patch<AudioSegment>(`/projects/${projectId}/audio/segments/${segmentId}`, data).then(r => r.data)

export const synthesize = (projectId: string, segmentId: number) =>
  client.post(`/projects/${projectId}/audio/segments/${segmentId}/synthesize`).then(r => r.data)

export const insertPause = (projectId: string, segmentId: number, durationMs = 500) =>
  client.post<AudioSegment>(`/projects/${projectId}/audio/segments/${segmentId}/pause`, { duration_ms: durationMs }).then(r => r.data)

export const getPreviewUrl = (projectId: string, segmentId: number, cacheBust?: string) => {
  const base = `/api/projects/${projectId}/audio/segments/${segmentId}/preview`
  return cacheBust ? `${base}?t=${cacheBust}` : base
}

export const deleteSegment = (projectId: string, segmentId: number) =>
  client.delete(`/projects/${projectId}/audio/segments/${segmentId}`).then(r => r.data)

export const deleteAllSegments = (projectId: string) =>
  client.delete(`/projects/${projectId}/audio/segments`).then(r => r.data)

export const uploadMasterAudio = (projectId: string, file: File, whisperModel = 'base') => {
  const form = new FormData()
  form.append('file', file)
  form.append('whisper_model', whisperModel)
  return client.post(`/projects/${projectId}/audio/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600_000, // 10 min — Whisper can be slow on first run
  }).then(r => r.data)
}

export const finalizeAudio = (projectId: string) =>
  client.post<{ status: string; segment_count: number; scenes_created: number }>(
    `/projects/${projectId}/audio/finalize`
  ).then(r => r.data)
