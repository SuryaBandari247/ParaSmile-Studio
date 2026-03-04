import client from './client'
import type { Project, ProjectCreate, ProjectUpdate } from '@/types'

export const createProject = (data: ProjectCreate) =>
  client.post<Project>('/projects', data).then(r => r.data)

export const listProjects = () =>
  client.get<Project[]>('/projects').then(r => r.data)

export const getProject = (id: string) =>
  client.get<Project>(`/projects/${id}`).then(r => r.data)

export const updateProject = (id: string, data: ProjectUpdate) =>
  client.patch<Project>(`/projects/${id}`, data).then(r => r.data)

export const deleteProject = (id: string) =>
  client.delete(`/projects/${id}`)
