import { useState, useEffect, useCallback, useRef } from 'react'
import * as visualsApi from '@/api/visuals'
import * as scriptsApi from '@/api/scripts'
import { StatusBadge } from '@/components/common/StatusBadge'
import { EffectBrowser } from '@/components/visual/EffectBrowser'
import type { Scene, FootageResult, WikimediaImageResult, PixabayVideoResult, UnsplashPhotoResult, WebSocketMessage, ScriptVersion, SuggestKeywordsResponse } from '@/types'

type SearchSource = 'pexels' | 'wikimedia' | 'pixabay' | 'unsplash' | 'all'

interface Props {
  projectId: string
  lastMessage: WebSocketMessage | null
}

export function VisualPanel({ projectId, lastMessage }: Props) {
  const [scenes, setScenes] = useState<Scene[]>([])
  const [searchResults, setSearchResults] = useState<Record<number, (FootageResult | WikimediaImageResult | PixabayVideoResult | UnsplashPhotoResult)[]>>({})
  const [searchQuery, setSearchQuery] = useState('')
  const [searchSource, setSearchSource] = useState<SearchSource>('all')
  const [searchingScene, setSearchingScene] = useState<number | null>(null)
  const [finalizedScripts, setFinalizedScripts] = useState<ScriptVersion[]>([])
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)
  const [rendering, setRendering] = useState<Set<number>>(new Set())
  const [renderError, setRenderError] = useState<string | null>(null)
  const [previewVersion, setPreviewVersion] = useState(0)
  const renderQueueRef = useRef<number[]>([])
  const renderActiveRef = useRef(false)
  const [suggestingScene, setSuggestingScene] = useState<number | null>(null)
  const [suggestions, setSuggestions] = useState<Record<number, SuggestKeywordsResponse>>({})
  const [selectedSuggestions, setSelectedSuggestions] = useState<Record<number, Set<number>>>({})
  const [editedKeywords, setEditedKeywords] = useState<Record<string, string>>({})
  const [suggestError, setSuggestError] = useState<Record<number, string>>({})
  const [showEffectBrowser, setShowEffectBrowser] = useState(false)
  const [effectBrowserTarget, setEffectBrowserTarget] = useState<number | null>(null)

  const load = useCallback(async () => {
    const s = await visualsApi.listScenes(projectId)
    setScenes(s)
    // Detect scenes that are already RUNNING (e.g. after page refresh) and track them
    const runningIds = s.filter(sc => sc.status === 'RUNNING').map(sc => sc.id)
    if (runningIds.length > 0) {
      setRendering(prev => {
        const next = new Set(prev)
        runningIds.forEach(id => next.add(id))
        return next
      })
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  // React to WebSocket job_completed/job_failed events — update scene instantly
  useEffect(() => {
    if (!lastMessage) return
    if (lastMessage.job_type !== 'render_scene') return

    if (lastMessage.event === 'job_completed' || lastMessage.event === 'job_failed') {
      // Refresh scenes to pick up new rendered_path / status
      load().then(() => {
        // Remove completed/failed scene from rendering set
        const sceneId = (lastMessage.data as Record<string, unknown>)?.scene_id as number | undefined
        if (sceneId) {
          setRendering(prev => { const s = new Set(prev); s.delete(sceneId); return s })
        }
        // Bump preview version to bust browser cache on video elements
        setPreviewVersion(v => v + 1)
      })
    }
  }, [lastMessage, load])

  // Polling fallback for when WebSocket events don't arrive
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    // Start polling when there are rendering scenes, stop when none
    if (rendering.size > 0 && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        const fresh = await visualsApi.listScenes(projectId)
        setScenes(fresh)
        const stillBusy = fresh.filter(s => rendering.has(s.id) && ['PENDING', 'RUNNING'].includes(s.status))
        if (stillBusy.length === 0) {
          setRendering(new Set())
          setPreviewVersion(v => v + 1)
          if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
        } else {
          // Update rendering set to only include still-busy scenes
          setRendering(new Set(stillBusy.map(s => s.id)))
        }
      }, 4000)
    }
    if (rendering.size === 0 && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [rendering.size, projectId])

  useEffect(() => {
    scriptsApi.listVersions(projectId).then(all => {
      setFinalizedScripts(all.filter(s => s.is_finalized))
    }).catch(() => {})
  }, [projectId])

  const handleGenerateScenes = async (scriptVersionId: number) => {
    setGenerating(true)
    setGenError(null)
    try {
      await visualsApi.createScenes(projectId, scriptVersionId)
      await load()
    } catch (e) {
      setGenError(e instanceof Error ? e.message : 'Failed to generate scenes')
    } finally { setGenerating(false) }
  }

  const handleSearch = async (sceneId: number) => {
    if (!searchQuery.trim()) return
    const results = await visualsApi.searchFootage(projectId, sceneId, searchQuery, searchSource)
    setSearchResults(prev => ({ ...prev, [sceneId]: results }))
  }

  const handleSelect = async (sceneId: number, path: string, source: SearchSource = 'pexels', attribution?: string, stockTitle?: string) => {
    await visualsApi.selectFootage(projectId, sceneId, path, source, attribution, stockTitle)
    setSearchResults(prev => { const n = { ...prev }; delete n[sceneId]; return n })
    setSearchingScene(null)
    load()
  }

  const handleToggleShowTitle = async (sceneId: number) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const updated = !scene.show_title
    await visualsApi.updateScene(projectId, sceneId, { show_title: updated } as Partial<Scene>)
    setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, show_title: updated } : s))
  }

  const handleAddScene = async () => {
    await visualsApi.addScene(projectId)
    load()
  }

  const handleDeleteScene = async (sceneId: number) => {
    if (!confirm('Remove this scene?')) return
    await visualsApi.deleteScene(projectId, sceneId)
    load()
  }

  const handleSuggestKeywords = async (sceneId: number) => {
    setSuggestingScene(sceneId)
    setSuggestError(prev => { const n = { ...prev }; delete n[sceneId]; return n })
    try {
      const result = await visualsApi.suggestKeywords(projectId, sceneId)
      setSuggestions(prev => ({ ...prev, [sceneId]: result }))
    } catch (e) {
      setSuggestError(prev => ({ ...prev, [sceneId]: e instanceof Error ? e.message : 'Failed to get suggestions' }))
    } finally {
      setSuggestingScene(null)
    }
  }

  // ── Clip timeline helpers ──────────────────────────────────────
  type ClipDef = { keywords: string; duration: number; source: string; speed?: number; selected_title?: string; selected_url?: string }

  const getClips = (scene: Scene): ClipDef[] => {
    const vd = scene.visual_data as Record<string, unknown>
    return (vd?.clips as ClipDef[]) || []
  }

  const saveClips = async (sceneId: number, clips: ClipDef[]) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const vd = { ...(scene.visual_data || {}), clips }
    // Reset status to PENDING so user sees they need to re-render
    const wasRendered = scene.status === 'RENDERED'
    await visualsApi.updateScene(projectId, sceneId, { visual_data: vd } as Partial<Scene>)
    setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, visual_data: vd, status: wasRendered ? 'PENDING' : s.status } : s))
  }

  const addClip = (sceneId: number) => {
    const clips = getClips(scenes.find(s => s.id === sceneId)!)
    saveClips(sceneId, [...clips, { keywords: '', duration: 4, source: 'auto' }])
  }

  const removeClip = (sceneId: number, idx: number) => {
    const clips = getClips(scenes.find(s => s.id === sceneId)!)
    saveClips(sceneId, clips.filter((_, i) => i !== idx))
  }

  const moveClip = (sceneId: number, idx: number, direction: -1 | 1) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const clips = [...getClips(scene)]
    const target = idx + direction
    if (target < 0 || target >= clips.length) return
    ;[clips[idx], clips[target]] = [clips[target], clips[idx]]
    saveClips(sceneId, clips)
  }

  // Per-clip inline search state: { sceneId-clipIdx: results[] }
  const [clipSearchResults, setClipSearchResults] = useState<Record<string, (FootageResult | WikimediaImageResult | PixabayVideoResult | UnsplashPhotoResult)[]>>({})
  const [clipSearching, setClipSearching] = useState<string | null>(null) // "sceneId-clipIdx"

  const handleClipSearch = async (sceneId: number, clipIdx: number, keywords: string, source: string) => {
    const key = `${sceneId}-${clipIdx}`
    if (!keywords.trim()) return
    setClipSearching(key)
    const apiSource = source === 'auto' ? 'pexels' : source
    const results = await visualsApi.searchFootage(projectId, sceneId, keywords, apiSource)
    setClipSearchResults(prev => ({ ...prev, [key]: results }))
    setClipSearching(null)
  }

  const handleClipSelect = async (sceneId: number, clipIdx: number, url: string, source: string, title?: string) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const clips = [...getClips(scene)]
    clips[clipIdx] = { ...clips[clipIdx], source, selected_title: title || clips[clipIdx].selected_title, selected_url: url }
    await saveClips(sceneId, clips)
    const key = `${sceneId}-${clipIdx}`
    setClipSearchResults(prev => { const n = { ...prev }; delete n[key]; return n })
  }

  const updateClip = (sceneId: number, idx: number, field: keyof ClipDef, value: string | number) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const clips = [...getClips(scene)]
    clips[idx] = { ...clips[idx], [field]: value }
    saveClips(sceneId, clips)
  }

  const initClipsFromScene = (scene: Scene): ClipDef[] => {
    const vd = scene.visual_data as Record<string, unknown>
    const keywords = (vd?.keywords as string[]) || []
    const title = (vd?.title as string) || (vd?.heading as string) || ''
    const sceneDuration = scene.target_duration || (scene.duration ?? 8)

    // Build keyword pool from scene data
    const keywordPool: string[] = []
    if (keywords.length > 0) keywordPool.push(...keywords)
    if (title && !keywordPool.includes(title)) keywordPool.push(title)
    if (keywordPool.length === 0) keywordPool.push('abstract technology')

    // Split into 2-3 clips depending on duration
    const clipCount = sceneDuration > 10 ? 3 : sceneDuration > 5 ? 2 : 1
    const clipDuration = Math.round((sceneDuration / clipCount) * 10) / 10

    return Array.from({ length: clipCount }, (_, i) => ({
      keywords: keywordPool[i % keywordPool.length] || keywordPool[0],
      duration: clipDuration,
      source: (vd?.source as string) || 'auto',
    }))
  }

  const [editingClips, setEditingClips] = useState<number | null>(null)

  const toggleClipsEditor = async (scene: Scene) => {
    if (editingClips === scene.id) {
      setEditingClips(null)
      return
    }
    // Pre-populate clips if empty
    const existing = getClips(scene)
    if (existing.length === 0) {
      const defaults = initClipsFromScene(scene)
      await saveClips(scene.id, defaults)
    }
    setEditingClips(scene.id)
  }

  // ── Parallel render queue (up to 4 concurrent) ──────────────────
  const RENDER_CONCURRENCY = 2

  const renderOneScene = useCallback(async (sceneId: number) => {
    setRendering(prev => new Set(prev).add(sceneId))
    try {
      await visualsApi.renderScene(projectId, sceneId)
      // Poll until done
      let done = false
      for (let i = 0; i < 300 && !done; i++) {
        await new Promise(r => setTimeout(r, 4000))
        try {
          const fresh = await visualsApi.listScenes(projectId)
          setScenes(fresh)
          const s = fresh.find(sc => sc.id === sceneId)
          if (s && s.status !== 'RUNNING' && s.status !== 'PENDING') {
            done = true
            setPreviewVersion(v => v + 1)
            if (s.status === 'FAILED') {
              setRenderError(prev => (prev ? prev + '\n' : '') + `Scene ${s.scene_number}: render failed`)
            }
          }
        } catch {
          // Poll failed (DB busy, network blip) — just retry next iteration
        }
      }
      if (!done) {
        setRenderError(prev => (prev ? prev + '\n' : '') + `Scene ${sceneId}: timed out`)
      }
    } catch (e: unknown) {
      // Extract meaningful error from axios response or fallback
      let msg = 'Render failed'
      if (e && typeof e === 'object' && 'response' in e) {
        const resp = (e as { response?: { data?: { detail?: string | { message?: string } }; status?: number } }).response
        const detail = resp?.data?.detail
        if (typeof detail === 'string') msg = detail
        else if (detail && typeof detail === 'object' && 'message' in detail) msg = String(detail.message)
        else if (resp?.status) msg = `Request failed with status code ${resp.status}`
      } else if (e instanceof Error) {
        msg = e.message
      }
      setRenderError(prev => (prev ? prev + '\n' : '') + `Scene ${sceneId}: ${msg}`)
    } finally {
      setRendering(prev => { const n = new Set(prev); n.delete(sceneId); return n })
    }
  }, [projectId])

  const processQueue = useCallback(async () => {
    if (renderActiveRef.current) return
    renderActiveRef.current = true

    const queue = [...renderQueueRef.current]
    renderQueueRef.current = []

    // Process in batches of RENDER_CONCURRENCY
    for (let i = 0; i < queue.length; i += RENDER_CONCURRENCY) {
      const batch = queue.slice(i, i + RENDER_CONCURRENCY)
      await Promise.all(batch.map(sceneId => renderOneScene(sceneId)))
    }

    renderActiveRef.current = false
  }, [renderOneScene])

  const handleRender = useCallback((sceneId: number) => {
    setRenderError(null)
    setRendering(prev => new Set(prev).add(sceneId))
    renderQueueRef.current.push(sceneId)
    processQueue()
  }, [processQueue])

  const handleRenderAll = useCallback(async (forceAll = false) => {
    setRenderError(null)
    // Refresh scene list to avoid stale IDs after regeneration
    const fresh = await visualsApi.listScenes(projectId)
    setScenes(fresh)
    const pending = forceAll
      ? fresh.filter(s => !rendering.has(s.id))
      : fresh.filter(s => s.status !== 'RENDERED' && !rendering.has(s.id))
    if (pending.length === 0) return
    // Immediately mark all as rendering so UI shows spinners
    setRendering(prev => {
      const next = new Set(prev)
      for (const scene of pending) next.add(scene.id)
      return next
    })
    for (const scene of pending) {
      renderQueueRef.current.push(scene.id)
    }
    processQueue()
  }, [rendering, processQueue, projectId])

  const handleDeleteAll = async () => {
    if (!confirm('Delete all scenes and clear stock cache? You can regenerate them from the script.')) return
    await visualsApi.deleteAllScenes(projectId)
    await visualsApi.clearStockCache(projectId)
    setScenes([])
    setRendering(new Set())
  }

  const handleClearCache = async () => {
    if (!confirm('Clear all cached stock footage? Next render will download fresh clips.')) return
    await visualsApi.clearStockCache(projectId)
  }

  const renderedCount = scenes.filter(s => s.status === 'RENDERED').length
  const allRendered = scenes.length > 0 && renderedCount === scenes.length

  return (
    <div className="space-y-6">
      {/* Effect Browser Modal */}
      {showEffectBrowser && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', justifyContent: 'center', alignItems: 'center', background: 'rgba(0,0,0,0.5)' }}>
          <div style={{ background: '#1a1a1a', borderRadius: '12px', maxWidth: '800px', width: '90%', maxHeight: '80vh', overflow: 'auto' }}>
            <EffectBrowser
              onClose={() => { setShowEffectBrowser(false); setEffectBrowserTarget(null) }}
              onApply={async (identifier, defaults) => {
                if (effectBrowserTarget != null) {
                  await visualsApi.updateScene(projectId, effectBrowserTarget, { visual_type: identifier, visual_data: defaults } as Partial<Scene>)
                  load()
                }
                setShowEffectBrowser(false)
                setEffectBrowserTarget(null)
              }}
            />
          </div>
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">Visual Scenes</h2>
          {scenes.length > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">{renderedCount}/{scenes.length} rendered</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {scenes.length > 0 && (
            <button type="button" onClick={() => setShowEffectBrowser(true)} className="px-3 py-1.5 bg-purple-50 text-purple-600 rounded-lg text-sm hover:bg-purple-100">Effect Browser</button>
          )}
          {scenes.length > 0 && (
            <button type="button" onClick={handleAddScene} className="px-3 py-1.5 bg-gray-50 text-gray-600 rounded-lg text-sm hover:bg-gray-100">+ Add Scene</button>
          )}
          {scenes.length > 0 && (
            <button type="button" onClick={handleClearCache} className="px-3 py-1.5 bg-orange-50 text-orange-600 rounded-lg text-sm hover:bg-orange-100">Clear Cache</button>
          )}
          {scenes.length > 0 && (
            <button type="button" onClick={handleDeleteAll} className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100">Delete All</button>
          )}
          {scenes.length > 0 && !allRendered && (
            <button
              type="button"
              onClick={() => handleRenderAll(false)}
              disabled={rendering.size > 0 || renderQueueRef.current.length > 0}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
            >
              {rendering.size > 0
                ? <><span className="animate-spin text-xs">⏳</span> Rendering {rendering.size} ({scenes.filter(s => s.status === 'RENDERED').length}/{scenes.length})...</>
                : 'Render All'}
            </button>
          )}
          {allRendered && (
            <button
              type="button"
              onClick={() => handleRenderAll(true)}
              disabled={rendering.size > 0}
              className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              {rendering.size > 0
                ? <><span className="animate-spin text-xs">⏳</span> Rendering {rendering.size} ({scenes.filter(s => s.status === 'RENDERED').length}/{scenes.length})...</>
                : '↻ Re-render All'}
            </button>
          )}
        </div>
      </div>

      {renderError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{renderError}</div>}

      {/* Empty state */}
      {scenes.length === 0 ? (
        <div className="space-y-3">
          {finalizedScripts.length === 0 ? (
            <p className="text-sm text-gray-500">No finalized scripts. Finalize a script first.</p>
          ) : (
            <div className="border rounded-lg p-4 bg-gray-50">
              <p className="text-sm font-medium mb-3">Generate visual scenes from a finalized script:</p>
              {finalizedScripts.map(s => {
                const cnt = ((s.script_json as Record<string, unknown>)?.scenes as unknown[])?.length ?? '?'
                return (
                  <div key={s.id} className="flex items-center justify-between border rounded-lg p-3 bg-white mb-2">
                    <span className="text-sm font-medium">{s.title} <span className="text-xs text-gray-400">v{s.version} · {cnt} scenes</span></span>
                    <button type="button" onClick={() => handleGenerateScenes(s.id)} disabled={generating} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                      {generating ? 'Generating...' : 'Generate Scenes'}
                    </button>
                  </div>
                )
              })}
              {genError && <p className="text-sm text-red-600 mt-2">{genError}</p>}
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Regenerate option */}
          {finalizedScripts.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-gray-500 hover:text-gray-700">Regenerate from a different script version</summary>
              <div className="mt-2 space-y-2">
                {finalizedScripts.map(s => (
                  <div key={s.id} className="flex items-center justify-between border rounded-lg p-3 bg-gray-50">
                    <span className="text-sm">{s.title} <span className="text-xs text-gray-400">v{s.version}</span></span>
                    <button type="button" onClick={() => handleGenerateScenes(s.id)} disabled={generating} className="px-3 py-1.5 bg-gray-600 text-white rounded-lg text-xs hover:bg-gray-700 disabled:opacity-50">
                      {generating ? 'Generating...' : 'Regenerate'}
                    </button>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Scene cards */}
          <div className="grid grid-cols-2 gap-4">
            {scenes.map(scene => {
              const isBusy = rendering.has(scene.id) || scene.status === 'RUNNING'
              const isRendered = scene.status === 'RENDERED'
              const isFailed = scene.status === 'FAILED'
              const hasChanges = scene.status === 'PENDING' && !!scene.rendered_path

              return (
                <div key={scene.id} className={`border rounded-lg overflow-hidden ${isRendered ? 'border-green-200' : isFailed ? 'border-red-200' : isBusy ? 'border-blue-200' : hasChanges ? 'border-orange-300' : 'border-gray-200'}`}>
                  <div className="aspect-video bg-gray-100 flex items-center justify-center relative">
                    {(isRendered || scene.rendered_path) ? (
                      <>
                        <video
                          key={`preview-${scene.id}-${previewVersion}`}
                          src={visualsApi.getPreviewUrl(projectId, scene.id, previewVersion)}
                          className="w-full h-full object-contain bg-black"
                          controls
                          muted
                          preload="metadata"
                          aria-label={`Preview scene ${scene.scene_number}`}
                        />
                        {hasChanges && (
                          <span className="absolute top-2 right-2 bg-orange-500 text-white text-xs px-2 py-0.5 rounded shadow">outdated — re-render</span>
                        )}
                      </>
                    ) : isBusy ? (
                      <div className="flex flex-col items-center gap-2">
                        <span className="animate-spin text-2xl">⏳</span>
                        <span className="text-xs text-blue-600">Rendering...</span>
                      </div>
                    ) : scene.stock_video_path ? (
                      <div className="flex flex-col items-center gap-2 p-3">
                        {(scene.visual_data as Record<string, unknown>)?.source === 'wikimedia' ? (
                          <>
                            <img src={scene.stock_video_path} alt="Selected from Wikimedia" className="max-h-24 rounded object-contain" />
                            <span className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded">📷 Wikimedia image selected</span>
                          </>
                        ) : (scene.visual_data as Record<string, unknown>)?.source === 'pixabay' ? (
                          <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">🎬 Pixabay footage selected</span>
                        ) : (scene.visual_data as Record<string, unknown>)?.source === 'unsplash' ? (
                          <>
                            <img src={scene.stock_video_path} alt="Selected from Unsplash" className="max-h-24 rounded object-contain" />
                            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded">📷 Unsplash photo selected</span>
                          </>
                        ) : (
                          <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">🎬 Pexels footage selected</span>
                        )}
                        {(scene.visual_data as Record<string, unknown>)?.stock_title && (
                          <span className="text-xs text-gray-500 mt-1 truncate max-w-full block px-2">{String((scene.visual_data as Record<string, unknown>).stock_title)}</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-400 text-sm">No preview</span>
                    )}
                  </div>
                  <div className="p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Scene {scene.scene_number}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">{scene.visual_type}</span>
                        <StatusBadge status={isBusy ? 'RUNNING' : scene.status} />
                      </div>
                    </div>

                    {/* Visual data summary */}
                    {scene.visual_data && (
                      <p className="text-xs text-gray-500 mb-2 truncate">
                        {String((scene.visual_data as Record<string, unknown>).title || (scene.visual_data as Record<string, unknown>).heading || '')}
                      </p>
                    )}

                    {/* Narration script text */}
                    {(scene.visual_data as Record<string, unknown>)?.narration_text && (
                      <details className="mb-2">
                        <summary className="text-xs text-indigo-600 cursor-pointer hover:text-indigo-800 select-none">📝 Script</summary>
                        <p className="mt-1 text-xs text-gray-600 bg-indigo-50 rounded p-2 leading-relaxed whitespace-pre-wrap">
                          {String((scene.visual_data as Record<string, unknown>).narration_text ?? '')}
                        </p>
                      </details>
                    )}

                    {/* Clip timeline controls */}
                    <div className="mb-2">
                      <div className="flex items-center gap-1 mb-1">
                        <button
                          type="button"
                          onClick={() => toggleClipsEditor(scene)}
                          className={`text-xs px-2 py-0.5 rounded ${getClips(scene).length > 0 ? 'bg-teal-50 text-teal-700' : 'bg-gray-50 text-gray-500'}`}
                        >
                          🎞 {getClips(scene).length > 0 ? `${getClips(scene).length} clips · ${getClips(scene).reduce((s, c) => s + c.duration, 0).toFixed(1)}s` : 'Auto clips'}
                        </button>
                        {scene.target_duration != null && scene.target_duration > 0 && (
                          <span className="text-xs text-gray-400">⏱ {scene.target_duration}s</span>
                        )}
                      </div>
                      {editingClips === scene.id && (
                        <div className="border rounded p-2 bg-gray-50 space-y-1.5">
                          {getClips(scene).map((clip, ci) => {
                            const clipKey = `${scene.id}-${ci}`
                            const clipResults = clipSearchResults[clipKey]
                            return (
                              <div key={ci} className="space-y-1">
                                <div className="flex items-center gap-1">
                                  <div className="flex flex-col">
                                    <button type="button" onClick={() => moveClip(scene.id, ci, -1)} disabled={ci === 0} className="text-xs text-gray-400 hover:text-gray-700 disabled:opacity-20 leading-none" aria-label={`Move clip ${ci + 1} up`}>▲</button>
                                    <button type="button" onClick={() => moveClip(scene.id, ci, 1)} disabled={ci === getClips(scene).length - 1} className="text-xs text-gray-400 hover:text-gray-700 disabled:opacity-20 leading-none" aria-label={`Move clip ${ci + 1} down`}>▼</button>
                                  </div>
                                  <span className="text-xs text-gray-400 w-4">{ci + 1}</span>
                                  <input
                                    value={clip.keywords}
                                    onChange={e => updateClip(scene.id, ci, 'keywords', e.target.value)}
                                    onBlur={() => { if (!clip.keywords.trim()) return; saveClips(scene.id, getClips(scenes.find(s => s.id === scene.id)!)) }}
                                    placeholder="keywords..."
                                    className="flex-1 border rounded px-1.5 py-0.5 text-xs min-w-0"
                                    aria-label={`Keywords for clip ${ci + 1}`}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => handleClipSearch(scene.id, ci, clip.keywords, clip.source)}
                                    disabled={clipSearching === clipKey || !clip.keywords.trim()}
                                    className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 disabled:opacity-40"
                                    title="Search footage for this clip"
                                    aria-label={`Search footage for clip ${ci + 1}`}
                                  >
                                    {clipSearching === clipKey ? '...' : '🔍'}
                                  </button>
                                  <input
                                    type="number"
                                    min="1"
                                    max="60"
                                    step="0.5"
                                    value={clip.duration}
                                    onChange={e => updateClip(scene.id, ci, 'duration', parseFloat(e.target.value) || 4)}
                                    className="w-12 border rounded px-1 py-0.5 text-xs"
                                    aria-label={`Duration for clip ${ci + 1}`}
                                  />
                                  <span className="text-xs text-gray-400">s</span>
                                  <select
                                    value={clip.speed ?? 1}
                                    onChange={e => updateClip(scene.id, ci, 'speed', parseFloat(e.target.value) || 1)}
                                    className="text-xs border rounded px-0.5 py-0.5 bg-white w-14"
                                    aria-label={`Speed for clip ${ci + 1}`}
                                    title="Playback speed"
                                  >
                                    <option value={0.25}>0.25×</option>
                                    <option value={0.5}>0.5×</option>
                                    <option value={0.75}>0.75×</option>
                                    <option value={1}>1×</option>
                                    <option value={1.5}>1.5×</option>
                                    <option value={2}>2×</option>
                                    <option value={3}>3×</option>
                                  </select>
                                  <select
                                    value={clip.source}
                                    onChange={e => updateClip(scene.id, ci, 'source', e.target.value)}
                                    className="text-xs border rounded px-0.5 py-0.5 bg-white"
                                    aria-label={`Source for clip ${ci + 1}`}
                                  >
                                    <option value="auto">Auto</option>
                                    <option value="pexels">Pexels</option>
                                    <option value="pixabay">Pixabay</option>
                                    <option value="wikimedia">Wikimedia</option>
                                    <option value="unsplash">Unsplash</option>
                                  </select>
                                  <button type="button" onClick={() => removeClip(scene.id, ci)} className="text-xs text-red-400 hover:text-red-600 px-1" aria-label={`Remove clip ${ci + 1}`}>✕</button>
                                </div>
                                {clip.selected_title && (
                                  <p className="ml-8 text-xs text-teal-600 truncate" title={clip.selected_title}>✓ {clip.selected_title}</p>
                                )}
                                {clipResults && clipResults.length > 0 && (
                                  <div className="ml-8 border rounded bg-white p-1 space-y-0.5 max-h-32 overflow-y-auto">
                                    {clipResults.slice(0, 5).map((f, fi) => {
                                      if ('license' in f) {
                                        const wf = f as WikimediaImageResult
                                        return (
                                          <div key={`wm-${fi}`} className="flex items-center gap-1.5 p-1 hover:bg-gray-50 rounded text-xs">
                                            <img src={wf.thumb_url} alt={wf.title} className="w-8 h-6 object-cover rounded" />
                                            <span className="truncate flex-1">{wf.title.replace('File:', '')}</span>
                                            <a href={wf.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 underline shrink-0 px-1" onClick={e => e.stopPropagation()} aria-label="Preview image">preview</a>
                                            <button type="button" onClick={() => handleClipSelect(scene.id, ci, wf.url, 'wikimedia', wf.title.replace('File:', ''))} className="text-green-600 hover:text-green-800 font-medium shrink-0 px-1" aria-label="Select">use</button>
                                          </div>
                                        )
                                      }
                                      if ('tags' in f) {
                                        const pxf = f as PixabayVideoResult
                                        return (
                                          <div key={`px-${fi}`} className="flex items-center gap-1.5 p-1 hover:bg-gray-50 rounded text-xs">
                                            <span>🎬</span>
                                            <span className="truncate flex-1">{pxf.tags || `#${pxf.video_id}`}</span>
                                            <span className="text-gray-400 shrink-0">{pxf.duration}s</span>
                                            <a href={pxf.url || pxf.preview_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 underline shrink-0 px-1" onClick={e => e.stopPropagation()} aria-label="Preview">preview</a>
                                            <button type="button" onClick={() => handleClipSelect(scene.id, ci, pxf.preview_url || pxf.url, 'pixabay', pxf.tags || `Pixabay #${pxf.video_id}`)} className="text-green-600 hover:text-green-800 font-medium shrink-0 px-1" aria-label="Select">use</button>
                                          </div>
                                        )
                                      }
                                      if ('photographer' in f) {
                                        const uf = f as UnsplashPhotoResult
                                        return (
                                          <div key={`us-${fi}`} className="flex items-center gap-1.5 p-1 hover:bg-gray-50 rounded text-xs">
                                            <img src={uf.thumb_url} alt={uf.description} className="w-8 h-6 object-cover rounded" />
                                            <span className="truncate flex-1">{uf.description || `by ${uf.photographer}`}</span>
                                            <a href={uf.page_url || uf.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 underline shrink-0 px-1" onClick={e => e.stopPropagation()} aria-label="Preview image">preview</a>
                                            <button type="button" onClick={() => handleClipSelect(scene.id, ci, uf.url, 'unsplash', uf.description || `Photo by ${uf.photographer}`)} className="text-green-600 hover:text-green-800 font-medium shrink-0 px-1" aria-label="Select">use</button>
                                          </div>
                                        )
                                      }
                                      const pf = f as FootageResult
                                      return (
                                        <div key={`pf-${fi}`} className="flex items-center gap-1.5 p-1 hover:bg-gray-50 rounded text-xs">
                                          <span>🎬</span>
                                          <span className="truncate flex-1 text-gray-600">{pf.url.replace(/\/$/, '').split('/').pop() || 'Pexels video'}</span>
                                          <span className="text-gray-400 shrink-0">{pf.duration}s</span>
                                          <a href={pf.url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:text-blue-700 underline shrink-0 px-1" onClick={e => e.stopPropagation()} aria-label="Preview">preview</a>
                                          <button type="button" onClick={() => handleClipSelect(scene.id, ci, pf.preview_url || pf.url, 'pexels', String(pf.url).replace(/\/$/, '').split('/').pop() || `Pexels #${pf.video_id}`)} className="text-green-600 hover:text-green-800 font-medium shrink-0 px-1" aria-label="Select">use</button>
                                        </div>
                                      )
                                    })}
                                    <button type="button" onClick={() => setClipSearchResults(prev => { const n = { ...prev }; delete n[clipKey]; return n })} className="text-xs text-gray-400 hover:text-gray-600 px-1">dismiss</button>
                                  </div>
                                )}
                              </div>
                            )
                          })}
                          <button type="button" onClick={() => addClip(scene.id)} className="text-xs text-teal-600 hover:text-teal-800 px-1">+ Add clip</button>
                          {getClips(scene).length === 0 && (
                            <p className="text-xs text-gray-400">No clips defined — orchestrator will auto-search based on scene keywords.</p>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex gap-1">
                      {hasChanges && (
                        <span className="text-xs text-orange-500 self-center mr-1">● changed</span>
                      )}
                      <button
                        type="button"
                        onClick={() => handleRender(scene.id)}
                        disabled={isBusy}
                        className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                          isBusy ? 'bg-blue-100 text-blue-500 cursor-wait' :
                          hasChanges ? 'bg-orange-500 text-white hover:bg-orange-600' :
                          isRendered ? 'bg-green-50 text-green-700 hover:bg-green-100' :
                          isFailed ? 'bg-red-50 text-red-700 hover:bg-red-100' :
                          'bg-blue-50 text-blue-700 hover:bg-blue-100'
                        }`}
                      >
                        {isBusy ? <><span className="animate-spin text-xs">⏳</span> Rendering...</> :
                         hasChanges ? '▶ Apply Changes' :
                         isRendered ? '↻ Re-render' :
                         isFailed ? '↻ Retry' :
                         '▶ Render'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setSearchingScene(searchingScene === scene.id ? null : scene.id)}
                        className="px-2 py-1 text-xs bg-gray-50 text-gray-600 rounded hover:bg-gray-100"
                      >
                        Search Footage
                      </button>
                      <button
                        type="button"
                        onClick={() => { setEffectBrowserTarget(scene.id); setShowEffectBrowser(true) }}
                        className="px-2 py-1 text-xs bg-purple-50 text-purple-600 rounded hover:bg-purple-100"
                      >
                        Browse Effects
                      </button>
                      {['stock_video', 'stock_with_text', 'stock_with_stat', 'stock_quote'].includes(scene.visual_type) && (
                        <button
                          type="button"
                          onClick={() => handleSuggestKeywords(scene.id)}
                          disabled={suggestingScene === scene.id}
                          className="px-2 py-1 text-xs bg-violet-50 text-violet-700 rounded hover:bg-violet-100 disabled:opacity-50 flex items-center gap-1"
                          aria-label={`Suggest keywords for scene ${scene.scene_number}`}
                        >
                          {suggestingScene === scene.id ? <><span className="animate-spin text-xs">⏳</span> Suggesting...</> : '🔑 Suggest Keywords'}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleToggleShowTitle(scene.id)}
                        className={`px-2 py-1 text-xs rounded ${scene.show_title ? 'bg-amber-50 text-amber-600 border border-amber-200' : 'bg-gray-50 text-gray-400'}`}
                        title={scene.show_title ? 'Text overlay ON — click to hide' : 'Text overlay OFF — click to show'}
                        aria-label={`Toggle text overlay for scene ${scene.scene_number}`}
                      >
                        Aa {scene.show_title ? '✓' : ''}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteScene(scene.id)}
                        className="px-2 py-1 text-xs bg-red-50 text-red-500 rounded hover:bg-red-100"
                        title="Remove scene"
                        aria-label={`Delete scene ${scene.scene_number}`}
                      >
                        ✕
                      </button>
                    </div>

                    {suggestError[scene.id] && (
                      <p className="text-xs text-red-500 mt-1">{suggestError[scene.id]}</p>
                    )}

                    {suggestions[scene.id] && (
                      <div className="mt-2 border border-violet-200 rounded-lg p-3 bg-violet-50/50 space-y-3">
                        {/* Keyword Categories */}
                        {Object.keys(suggestions[scene.id].keyword_categories).length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-violet-700 mb-1">📂 Keyword Map</p>
                            <div className="flex flex-wrap gap-1">
                              {Object.entries(suggestions[scene.id].keyword_categories).map(([cat, kws]) => (
                                kws.length > 0 && (
                                  <span key={cat} className="text-xs bg-white border border-violet-200 rounded px-1.5 py-0.5">
                                    <span className="text-violet-500 font-medium">{cat}:</span> {kws.join(', ')}
                                  </span>
                                )
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Narrative Beats */}
                        {suggestions[scene.id].narrative_beats.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-violet-700 mb-1">🎬 Narrative Beats</p>
                            <div className="space-y-1">
                              {suggestions[scene.id].narrative_beats.map((beat, bi) => (
                                <div key={bi} className="text-xs bg-white border border-violet-100 rounded p-1.5 flex items-start gap-1.5">
                                  {beat.timestamp_hint && <span className="text-violet-400 shrink-0">[{beat.timestamp_hint}]</span>}
                                  <span className="text-gray-700">{beat.beat}</span>
                                  {beat.suggested_keywords.length > 0 && (
                                    <span className="text-violet-500 shrink-0">→ {beat.suggested_keywords.join(', ')}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Ranked Suggestions */}
                        <div>
                          <p className="text-xs font-medium text-violet-700 mb-1">🔑 Suggestions (click to select)</p>
                          <div className="space-y-1">
                            {suggestions[scene.id].suggestions.map(s => {
                              const isSelected = selectedSuggestions[scene.id]?.has(s.rank)
                              const editKey = `${scene.id}-${s.rank}`
                              const displayKeyword = editedKeywords[editKey] ?? s.keyword
                              return (
                                <div
                                  key={s.rank}
                                  className={`flex items-center gap-1.5 p-1.5 rounded text-xs cursor-pointer transition-colors ${isSelected ? 'bg-violet-200 border border-violet-300' : 'bg-white border border-gray-100 hover:border-violet-200'}`}
                                  onClick={() => {
                                    setSelectedSuggestions(prev => {
                                      const current = new Set(prev[scene.id] || [])
                                      if (current.has(s.rank)) current.delete(s.rank)
                                      else current.add(s.rank)
                                      return { ...prev, [scene.id]: current }
                                    })
                                  }}
                                >
                                  <span className="text-violet-400 font-mono w-4 shrink-0">#{s.rank}</span>
                                  {s.category && <span className="text-violet-300 shrink-0">[{s.category}]</span>}
                                  <input
                                    value={displayKeyword}
                                    onChange={e => {
                                      e.stopPropagation()
                                      setEditedKeywords(prev => ({ ...prev, [editKey]: e.target.value }))
                                    }}
                                    onClick={e => e.stopPropagation()}
                                    className="flex-1 bg-transparent border-b border-transparent hover:border-gray-300 focus:border-violet-400 outline-none px-0.5 min-w-0"
                                    aria-label={`Edit keyword suggestion ${s.rank}`}
                                  />
                                  {s.visual_synonym && s.original_term && (
                                    <span className="text-gray-400 shrink-0 text-xs">{s.original_term} → {s.visual_synonym}</span>
                                  )}
                                  {s.source_hints && (
                                    <span className="text-gray-300 shrink-0" title={Object.entries(s.source_hints).map(([k,v]) => `${k}: ${v}`).join('\n')}>📋</span>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>

                        {/* Aesthetic Hints */}
                        {suggestions[scene.id].aesthetic_hints.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap">
                            <span className="text-xs text-violet-500">🎨 Style:</span>
                            {suggestions[scene.id].aesthetic_hints.map((hint, hi) => (
                              <span key={hi} className="text-xs bg-violet-100 text-violet-600 rounded px-1.5 py-0.5">{hint}</span>
                            ))}
                          </div>
                        )}

                        {/* Accept / Dismiss actions */}
                        <div className="flex gap-2 pt-1">
                          <button
                            type="button"
                            onClick={async () => {
                              const selected = selectedSuggestions[scene.id]
                              if (!selected || selected.size === 0) return
                              const sceneData = scenes.find(sc => sc.id === scene.id)
                              if (!sceneData) return
                              const existingKeywords = ((sceneData.visual_data as Record<string, unknown>)?.keywords as string[]) || []
                              const acceptedKeywords = suggestions[scene.id].suggestions
                                .filter(s => selected.has(s.rank))
                                .map(s => {
                                  const editKey = `${scene.id}-${s.rank}`
                                  return editedKeywords[editKey] ?? s.keyword
                                })
                              const merged = [...acceptedKeywords, ...existingKeywords]
                              const vd = { ...(sceneData.visual_data || {}), keywords: merged }
                              await visualsApi.updateScene(projectId, scene.id, { visual_data: vd } as Partial<Scene>)
                              setScenes(prev => prev.map(sc => sc.id === scene.id ? { ...sc, visual_data: vd } : sc))
                              setSuggestions(prev => { const n = { ...prev }; delete n[scene.id]; return n })
                              setSelectedSuggestions(prev => { const n = { ...prev }; delete n[scene.id]; return n })
                              setEditedKeywords(prev => {
                                const n = { ...prev }
                                Object.keys(n).forEach(k => { if (k.startsWith(`${scene.id}-`)) delete n[k] })
                                return n
                              })
                            }}
                            disabled={!selectedSuggestions[scene.id] || selectedSuggestions[scene.id]?.size === 0}
                            className="px-3 py-1 text-xs bg-violet-600 text-white rounded hover:bg-violet-700 disabled:opacity-40"
                          >
                            ✓ Accept Selected ({selectedSuggestions[scene.id]?.size || 0})
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setSuggestions(prev => { const n = { ...prev }; delete n[scene.id]; return n })
                              setSelectedSuggestions(prev => { const n = { ...prev }; delete n[scene.id]; return n })
                              setEditedKeywords(prev => {
                                const n = { ...prev }
                                Object.keys(n).forEach(k => { if (k.startsWith(`${scene.id}-`)) delete n[k] })
                                return n
                              })
                            }}
                            className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    )}

                    {searchingScene === scene.id && (
                      <div className="mt-2">
                        <div className="flex gap-1 mb-1">
                          <button
                            type="button"
                            onClick={() => { setSearchSource('all'); setSearchResults(prev => { const n = { ...prev }; delete n[scene.id]; return n }) }}
                            className={`px-2 py-0.5 text-xs rounded ${searchSource === 'all' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                          >All</button>
                          <button
                            type="button"
                            onClick={() => { setSearchSource('pexels'); setSearchResults(prev => { const n = { ...prev }; delete n[scene.id]; return n }) }}
                            className={`px-2 py-0.5 text-xs rounded ${searchSource === 'pexels' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                          >Pexels</button>
                          <button
                            type="button"
                            onClick={() => { setSearchSource('pixabay'); setSearchResults(prev => { const n = { ...prev }; delete n[scene.id]; return n }) }}
                            className={`px-2 py-0.5 text-xs rounded ${searchSource === 'pixabay' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                          >Pixabay</button>
                          <button
                            type="button"
                            onClick={() => { setSearchSource('wikimedia'); setSearchResults(prev => { const n = { ...prev }; delete n[scene.id]; return n }) }}
                            className={`px-2 py-0.5 text-xs rounded ${searchSource === 'wikimedia' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                          >Wikimedia</button>
                          <button
                            type="button"
                            onClick={() => { setSearchSource('unsplash'); setSearchResults(prev => { const n = { ...prev }; delete n[scene.id]; return n }) }}
                            className={`px-2 py-0.5 text-xs rounded ${searchSource === 'unsplash' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                          >Unsplash</button>
                        </div>
                        <div className="flex gap-1">
                          <input
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSearch(scene.id)}
                            className="flex-1 border rounded px-2 py-1 text-xs"
                            placeholder={searchSource === 'wikimedia' ? 'Search Wikimedia images...' : searchSource === 'unsplash' ? 'Search Unsplash photos...' : `Search ${searchSource === 'pixabay' ? 'Pixabay' : 'Pexels'} videos...`}
                            aria-label={`Search ${searchSource} footage for scene ${scene.scene_number}`}
                          />
                          <button type="button" onClick={() => handleSearch(scene.id)} className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200">Go</button>
                        </div>
                        {searchResults[scene.id]?.map((f, idx) => {
                          const src = (f as Record<string, unknown>)._source as string | undefined
                          const srcBadge = src ? <span className={`text-xs px-1 rounded ${src === 'pexels' ? 'bg-blue-50 text-blue-500' : src === 'pixabay' ? 'bg-green-50 text-green-500' : src === 'unsplash' ? 'bg-amber-50 text-amber-600' : 'bg-purple-50 text-purple-500'}`}>{src}</span> : null
                          if ('license' in f) {
                            // Wikimedia image result
                            const wf = f as WikimediaImageResult
                            return (
                              <div key={`wm-${idx}`} className="flex items-center gap-2 mt-1 p-1.5 hover:bg-gray-50 rounded border border-gray-100">
                                <img src={wf.thumb_url} alt={wf.title} className="w-12 h-8 object-cover rounded" />
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs text-gray-700 truncate">{srcBadge} {wf.title.replace('File:', '')}</p>
                                  <p className="text-xs text-gray-400">{wf.width}×{wf.height} · {wf.license}</p>
                                </div>
                                <a href={wf.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:text-blue-700 underline shrink-0 px-1" aria-label="Preview image">preview</a>
                                <button type="button" onClick={() => handleSelect(scene.id, wf.url, 'wikimedia', wf.attribution, wf.title.replace('File:', ''))} className="text-xs text-green-600 hover:text-green-800 font-medium shrink-0 px-1 border border-green-200 rounded" aria-label="Select footage">use</button>
                              </div>
                            )
                          }
                          if ('tags' in f) {
                            // Pixabay video result
                            const pxf = f as PixabayVideoResult
                            return (
                              <div key={`px-${pxf.video_id}`} className="flex items-center gap-2 mt-1 p-1.5 hover:bg-gray-50 rounded border border-gray-100">
                                <span className="text-lg">🎬</span>
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs text-gray-700 truncate">{srcBadge} {pxf.tags || `Pixabay #${pxf.video_id}`}</p>
                                  <p className="text-xs text-gray-400">{pxf.duration}s · {pxf.width}×{pxf.height} · CC0</p>
                                </div>
                                <a href={pxf.url || pxf.preview_url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:text-blue-700 underline shrink-0 px-1" aria-label="Preview video">preview</a>
                                <button type="button" onClick={() => handleSelect(scene.id, pxf.url, 'pixabay', undefined, pxf.tags || `Pixabay #${pxf.video_id}`)} className="text-xs text-green-600 hover:text-green-800 font-medium shrink-0 px-1 border border-green-200 rounded" aria-label="Select footage">use</button>
                              </div>
                            )
                          }
                          if ('photographer' in f) {
                            // Unsplash photo result
                            const uf = f as UnsplashPhotoResult
                            return (
                              <div key={`us-${uf.photo_id}`} className="flex items-center gap-2 mt-1 p-1.5 hover:bg-gray-50 rounded border border-gray-100">
                                <img src={uf.thumb_url} alt={uf.description} className="w-12 h-8 object-cover rounded" />
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs text-gray-700 truncate">{srcBadge} {uf.description || `Photo by ${uf.photographer}`}</p>
                                  <p className="text-xs text-gray-400">{uf.width}×{uf.height} · by {uf.photographer}</p>
                                </div>
                                <a href={uf.page_url || uf.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:text-blue-700 underline shrink-0 px-1" aria-label="Preview image">preview</a>
                                <button type="button" onClick={() => handleSelect(scene.id, uf.url, 'unsplash', `Photo by ${uf.photographer} on Unsplash`, uf.description || `Photo by ${uf.photographer}`)} className="text-xs text-green-600 hover:text-green-800 font-medium shrink-0 px-1 border border-green-200 rounded" aria-label="Select footage">use</button>
                              </div>
                            )
                          }
                          // Pexels video result
                          const pf = f as FootageResult
                          return (
                            <div key={pf.video_id} className="flex items-center gap-2 mt-1 p-1 hover:bg-gray-50 rounded border border-gray-100">
                              <span className="text-lg">🎬</span>
                              <div className="flex-1 min-w-0">
                                <p className="text-xs text-gray-600 truncate">{srcBadge} {String(pf.url).replace(/\/$/, '').split('/').pop() || 'Pexels video'}</p>
                                <p className="text-xs text-gray-400">{pf.duration}s · {pf.width}×{pf.height}</p>
                              </div>
                              <a href={pf.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-500 hover:text-blue-700 underline shrink-0 px-1" aria-label="Preview video">preview</a>
                              <button type="button" onClick={() => handleSelect(scene.id, pf.url, 'pexels', undefined, String(pf.url).replace(/\/$/, '').split('/').pop() || `Pexels #${pf.video_id}`)} className="text-xs text-green-600 hover:text-green-800 font-medium shrink-0 px-1 border border-green-200 rounded" aria-label="Select footage">use</button>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
