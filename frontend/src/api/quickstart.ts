import client from './client'
import type { Topic } from '@/types'

export const getRecentTopics = (limit = 20) =>
  client.get<Topic[]>('/topics/recent', { params: { limit } }).then(r => r.data)

export const quickStart = (data: { title: string; topic?: string; description?: string }) =>
  client.post<{ project: Record<string, unknown>; topic: Record<string, unknown> | null }>('/quick-start', data).then(r => r.data)

export const researchAllSources = (projectId?: string) =>
  client.post<{ project_id: string; jobs: Array<{ source: string; status: string }> }>(
    '/research/all-sources',
    null,
    { params: projectId ? { project_id: projectId } : {} }
  ).then(r => r.data)
