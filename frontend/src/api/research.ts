import client from './client'

export const searchYouTube = (projectId: string, keywords?: string[]) =>
  client.post(`/projects/${projectId}/research/youtube`, keywords ? { keywords } : {}).then(r => r.data)

export const searchReddit = (projectId: string) =>
  client.post(`/projects/${projectId}/research/reddit`).then(r => r.data)

export const searchTrends = (projectId: string) =>
  client.post(`/projects/${projectId}/research/trends`).then(r => r.data)

export const searchFinance = (projectId: string) =>
  client.post(`/projects/${projectId}/research/finance`).then(r => r.data)

export const searchWikipedia = (projectId: string) =>
  client.post(`/projects/${projectId}/research/wikipedia`).then(r => r.data)

export const crossReference = (projectId: string) =>
  client.post(`/projects/${projectId}/research/cross-reference`).then(r => r.data)

export const getResults = (projectId: string) =>
  client.get(`/projects/${projectId}/research/results`).then(r => r.data)
