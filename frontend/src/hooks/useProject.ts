import { useState, useEffect, useCallback } from 'react'
import { getProject } from '@/api/projects'
import type { Project } from '@/types'

export function useProject(projectId: string | undefined) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const p = await getProject(projectId)
      setProject(p)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => { refresh() }, [refresh])

  return { project, loading, error, refresh, setProject }
}
