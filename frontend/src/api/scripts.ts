import client from './client'
import type { ScriptVersion, ScriptVersionCreate, ScriptVersionUpdate, DiffResult } from '@/types'

export const listVersions = (projectId: string) =>
  client.get<ScriptVersion[]>(`/projects/${projectId}/scripts`).then(r => r.data)

export const createVersion = (projectId: string, data: ScriptVersionCreate) =>
  client.post<ScriptVersion>(`/projects/${projectId}/scripts`, data).then(r => r.data)

export const getVersion = (projectId: string, versionId: number) =>
  client.get<ScriptVersion>(`/projects/${projectId}/scripts/${versionId}`).then(r => r.data)

export const updateVersion = (projectId: string, versionId: number, data: ScriptVersionUpdate) =>
  client.patch<ScriptVersion>(`/projects/${projectId}/scripts/${versionId}`, data).then(r => r.data)

export const finalize = (projectId: string, versionId: number) =>
  client.post<ScriptVersion>(`/projects/${projectId}/scripts/${versionId}/finalize`).then(r => r.data)

export const getDiff = (projectId: string, v1: number, v2: number) =>
  client.get<DiffResult>(`/projects/${projectId}/scripts/diff`, { params: { v1, v2 } }).then(r => r.data)

export const generateFromRaw = (projectId: string, data: { topic_id: string; title: string; raw_text: string }) =>
  client.post<ScriptVersion>(`/projects/${projectId}/scripts/generate`, data).then(r => r.data)

export const deleteAll = (projectId: string) =>
  client.delete(`/projects/${projectId}/scripts`).then(r => r.data)
export const importJson = (projectId: string, data: { script_json: Record<string, unknown>; title?: string }) =>
  client.post<ScriptVersion>(`/projects/${projectId}/scripts/import`, data).then(r => r.data)

export const enrichKeywords = (projectId: string, versionId: number) =>
  client.post<ScriptVersion>(`/projects/${projectId}/scripts/${versionId}/enrich-keywords`).then(r => r.data)
