import client from './client'
import type { Scene, FootageResult, WikimediaImageResult, PixabayVideoResult, UnsplashPhotoResult, SuggestKeywordsResponse } from '@/types'

export const listScenes = (projectId: string) =>
  client.get<Scene[]>(`/projects/${projectId}/scenes`).then(r => r.data)

export const createScenes = (projectId: string, scriptVersionId: number) =>
  client.post<Scene[]>(`/projects/${projectId}/scenes`, { script_version_id: scriptVersionId }).then(r => r.data)

export const updateScene = (projectId: string, sceneId: number, data: Partial<Scene>) =>
  client.patch<Scene>(`/projects/${projectId}/scenes/${sceneId}`, data).then(r => r.data)

export const searchFootage = (projectId: string, sceneId: number, query: string, source: string = 'pexels') =>
  client.post<(FootageResult | WikimediaImageResult | PixabayVideoResult | UnsplashPhotoResult)[]>(`/projects/${projectId}/scenes/${sceneId}/search-footage`, { query, source }).then(r => r.data)

export const selectFootage = (projectId: string, sceneId: number, stockVideoPath: string, source: string = 'pexels', attribution?: string, stockTitle?: string) =>
  client.post<Scene>(`/projects/${projectId}/scenes/${sceneId}/select-footage`, { stock_video_path: stockVideoPath, source, attribution, stock_title: stockTitle }).then(r => r.data)

export const renderScene = (projectId: string, sceneId: number) =>
  client.post(`/projects/${projectId}/scenes/${sceneId}/render`).then(r => r.data)

export const getPreviewUrl = (projectId: string, sceneId: number, version?: number) =>
  `/api/projects/${projectId}/scenes/${sceneId}/preview${version ? `?v=${version}` : ''}`

export const deleteAllScenes = (projectId: string) =>
  client.delete(`/projects/${projectId}/scenes`).then(r => r.data)

export const addScene = (projectId: string, data: { visual_type?: string; visual_data?: Record<string, unknown>; target_duration?: number; clip_count?: number } = {}) =>
  client.post<Scene>(`/projects/${projectId}/scenes/add`, data).then(r => r.data)

export const deleteScene = (projectId: string, sceneId: number) =>
  client.delete(`/projects/${projectId}/scenes/${sceneId}`).then(r => r.data)

export const clearStockCache = (projectId: string) =>
  client.post<Record<string, number>>(`/projects/${projectId}/scenes/clear-cache`).then(r => r.data)

export const suggestKeywords = (projectId: string, sceneId: number) =>
  client.post<SuggestKeywordsResponse>(`/projects/${projectId}/scenes/${sceneId}/suggest-keywords`).then(r => r.data)
