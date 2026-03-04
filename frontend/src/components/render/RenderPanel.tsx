import { useState, useEffect, useCallback } from 'react'
import client from '@/api/client'
import * as visualsApi from '@/api/visuals'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Scene, WebSocketMessage } from '@/types'

const TRANSITION_GROUPS: { label: string; options: string[] }[] = [
  { label: 'Clean', options: ['none', 'fade', 'fadeblack', 'fadewhite', 'dissolve'] },
  { label: 'Smooth', options: ['smoothleft', 'smoothright', 'smoothup', 'smoothdown'] },
  { label: 'Directional', options: ['wipeleft', 'wiperight', 'wipeup', 'wipedown', 'slideleft', 'slideright', 'slideup', 'slidedown'] },
  { label: 'Geometric', options: ['circlecrop', 'circleclose', 'circleopen', 'rectcrop', 'diagtl', 'diagtr', 'diagbl', 'diagbr', 'radial'] },
  { label: 'Reveal', options: ['horzopen', 'horzclose', 'vertopen', 'vertclose', 'revealleft', 'revealright', 'revealup', 'revealdown'] },
  { label: 'Cover', options: ['coverleft', 'coverright', 'coverup', 'coverdown'] },
  { label: 'Stylized', options: ['pixelize', 'zoomin', 'squeezeh', 'squeezev'] },
  { label: 'Glitch', options: ['hlwind', 'hrwind', 'vuwind', 'vdwind', 'hlslice', 'hrslice', 'vuslice', 'vdslice'] },
]

const EFFECT_GROUPS: { label: string; options: { value: string; label: string }[] }[] = [
  { label: 'Lighting', options: [
    { value: 'vignette', label: 'Vignette' },
    { value: 'vignette_strong', label: 'Vignette (Strong)' },
    { value: 'brightness_boost', label: 'Brightness Boost' },
    { value: 'darken', label: 'Darken' },
  ]},
  { label: 'Color', options: [
    { value: 'color_grade', label: 'Color Grade' },
    { value: 'desaturate', label: 'Desaturate' },
    { value: 'warm_tone', label: 'Warm Tone' },
    { value: 'cool_tone', label: 'Cool Tone' },
    { value: 'high_contrast', label: 'High Contrast' },
  ]},
  { label: 'Motion', options: [
    { value: 'ken_burns', label: 'Ken Burns Zoom' },
  ]},
  { label: 'Blur', options: [
    { value: 'blur_edges', label: 'Blur Edges' },
    { value: 'sharpen', label: 'Sharpen' },
  ]},
]

interface RenderVersion {
  job_id: string
  status: string
  output: Record<string, unknown> | null
  error: string | null
  created_at: string
  is_latest: boolean
  has_file: boolean
}

interface Props {
  projectId: string
  lastMessage: WebSocketMessage | null
}

export function RenderPanel({ projectId, lastMessage }: Props) {
  const [scenes, setScenes] = useState<Scene[]>([])
  const [versions, setVersions] = useState<RenderVersion[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [progressMsg, setProgressMsg] = useState('')
  const [musicFile, setMusicFile] = useState<File | null>(null)
  const [volume, setVolume] = useState(80)
  const [fadeIn, setFadeIn] = useState(1000)
  const [fadeOut, setFadeOut] = useState(2000)

  const loadScenes = useCallback(async () => {
    const { data } = await client.get<Scene[]>(`/projects/${projectId}/scenes`)
    setScenes(data)
  }, [projectId])

  const loadHistory = useCallback(async () => {
    try {
      const { data } = await client.get<RenderVersion[]>(`/projects/${projectId}/render/history`)
      setVersions(data)
      // Auto-select latest with a file
      if (!selectedJobId || !data.find(v => v.job_id === selectedJobId)) {
        const latest = data.find(v => v.is_latest && v.has_file)
        if (latest) setSelectedJobId(latest.job_id)
      }
    } catch { /* no renders yet */ }
  }, [projectId, selectedJobId])

  useEffect(() => { loadScenes(); loadHistory() }, [loadScenes, loadHistory])

  useEffect(() => {
    if (!lastMessage) return
    if (lastMessage.event === 'job_progress' && lastMessage.job_type === 'render_final') {
      const d = lastMessage.data
      setProgress(d.progress as number)
      setProgressMsg(d.message as string || '')
    }
    if (lastMessage.event === 'job_completed' && lastMessage.job_type === 'render_final') {
      setProgress(null)
      loadHistory()
    }
  }, [lastMessage, loadHistory])

  const startRender = async () => {
    setProgress(0)
    setProgressMsg('Starting render...')
    try {
      const { data } = await client.post(`/projects/${projectId}/render`)
      // Auto-select the new render
      if (data.job_id) setSelectedJobId(data.job_id)
      setProgress(null)
      await loadHistory()
    } catch {
      setProgress(null)
    }
  }

  const uploadMusic = async () => {
    if (!musicFile) return
    const form = new FormData()
    form.append('file', musicFile)
    await client.post(`/projects/${projectId}/music/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    setMusicFile(null)
  }

  const saveSettings = async () => {
    await client.patch(`/projects/${projectId}/music/settings`, {
      volume, fade_in_ms: fadeIn, fade_out_ms: fadeOut,
    })
  }

  const reorder = async (sceneIds: number[]) => {
    await client.post(`/projects/${projectId}/render/reorder`, { scene_ids: sceneIds })
    loadScenes()
  }

  const moveScene = (idx: number, dir: -1 | 1) => {
    const ids = scenes.map(s => s.id)
    const newIdx = idx + dir
    if (newIdx < 0 || newIdx >= ids.length) return
    ;[ids[idx], ids[newIdx]] = [ids[newIdx], ids[idx]]
    reorder(ids)
  }

  const updateTransition = async (sceneId: number, transition: string) => {
    await visualsApi.updateScene(projectId, sceneId, { transition })
    setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, transition } : s))
  }

  const toggleEffect = async (sceneId: number, effect: string) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const current = scene.effects || []
    const updated = current.includes(effect)
      ? current.filter(e => e !== effect)
      : [...current, effect]
    await visualsApi.updateScene(projectId, sceneId, { effects: updated } as Partial<Scene>)
    setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, effects: updated } : s))
  }

  const toggleShowTitle = async (sceneId: number) => {
    const scene = scenes.find(s => s.id === sceneId)
    if (!scene) return
    const updated = !scene.show_title
    await visualsApi.updateScene(projectId, sceneId, { show_title: updated } as Partial<Scene>)
    setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, show_title: updated } : s))
  }

  const [effectsOpen, setEffectsOpen] = useState<number | null>(null)

  const selectedVersion = versions.find(v => v.job_id === selectedJobId)
  const videoUrl = selectedJobId
    ? `/api/projects/${projectId}/render/output?job_id=${selectedJobId}`
    : `/api/projects/${projectId}/render/output`

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-medium">Render</h2>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="font-medium mb-3">Scene Order</h3>
          {scenes.length === 0 ? (
            <p className="text-sm text-gray-500">No scenes to render.</p>
          ) : (
            <div className="space-y-2">
              {scenes.map((s, idx) => (
                <div key={s.id} className="flex items-center gap-2 border rounded-lg p-2">
                  <div className="flex flex-col gap-0.5">
                    <button type="button" onClick={() => moveScene(idx, -1)} disabled={idx === 0} className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-30" aria-label="Move up">▲</button>
                    <button type="button" onClick={() => moveScene(idx, 1)} disabled={idx === scenes.length - 1} className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-30" aria-label="Move down">▼</button>
                  </div>
                  <span className="text-sm flex-1">Scene {s.scene_number}</span>
                  <span className="text-xs text-gray-400">{s.visual_type}</span>
                  {s.duration != null && (
                    <span className="text-xs text-gray-500 font-mono">{s.duration.toFixed(1)}s</span>
                  )}
                  <select
                    value={s.transition || 'fade'}
                    onChange={e => updateTransition(s.id, e.target.value)}
                    className="text-xs border rounded px-1 py-0.5 bg-white text-purple-600"
                    aria-label={`Transition for scene ${s.scene_number}`}
                  >
                    {TRANSITION_GROUPS.map(g => (
                      <optgroup key={g.label} label={g.label}>
                        {g.options.map(t => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => toggleShowTitle(s.id)}
                      className={`text-xs border rounded px-1.5 py-0.5 ${s.show_title ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-white text-gray-400'}`}
                      aria-label={`Toggle text overlay for scene ${s.scene_number}`}
                      title={s.show_title ? 'Text overlay ON' : 'Text overlay OFF'}
                    >
                      Aa
                    </button>
                  </div>
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setEffectsOpen(effectsOpen === s.id ? null : s.id)}
                      className={`text-xs border rounded px-1.5 py-0.5 ${(s.effects?.length || 0) > 0 ? 'bg-indigo-50 text-indigo-600 border-indigo-200' : 'bg-white text-gray-500'}`}
                      aria-label={`Effects for scene ${s.scene_number}`}
                    >
                      FX {(s.effects?.length || 0) > 0 ? `(${s.effects.length})` : ''}
                    </button>
                    {effectsOpen === s.id && (
                      <div className="absolute right-0 top-7 z-10 bg-white border rounded-lg shadow-lg p-2 w-48 max-h-60 overflow-y-auto">
                        {EFFECT_GROUPS.map(g => (
                          <div key={g.label} className="mb-1.5">
                            <p className="text-xs font-medium text-gray-400 px-1 mb-0.5">{g.label}</p>
                            {g.options.map(opt => (
                              <label key={opt.value} className="flex items-center gap-1.5 px-1 py-0.5 hover:bg-gray-50 rounded cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={(s.effects || []).includes(opt.value)}
                                  onChange={() => toggleEffect(s.id, opt.value)}
                                  className="w-3 h-3"
                                />
                                <span className="text-xs text-gray-700">{opt.label}</span>
                              </label>
                            ))}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <StatusBadge status={s.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium mb-3">Background Music</h3>
            <div className="flex gap-2 items-center mb-3">
              <input
                type="file"
                accept=".mp3,.wav"
                onChange={e => setMusicFile(e.target.files?.[0] ?? null)}
                className="text-sm"
                aria-label="Upload music file"
              />
              {musicFile && (
                <button type="button" onClick={uploadMusic} className="px-3 py-1 text-xs bg-blue-600 text-white rounded">Upload</button>
              )}
            </div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm">
                Volume
                <input type="range" min="0" max="100" value={volume} onChange={e => setVolume(Number(e.target.value))} className="flex-1" />
                <span className="text-xs w-8">{volume}%</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                Fade In
                <input type="number" value={fadeIn} onChange={e => setFadeIn(Number(e.target.value))} className="border rounded px-2 py-1 text-xs w-20" />
                <span className="text-xs">ms</span>
              </label>
              <label className="flex items-center gap-2 text-sm">
                Fade Out
                <input type="number" value={fadeOut} onChange={e => setFadeOut(Number(e.target.value))} className="border rounded px-2 py-1 text-xs w-20" />
                <span className="text-xs">ms</span>
              </label>
              <button type="button" onClick={saveSettings} className="px-3 py-1.5 text-xs bg-gray-100 rounded hover:bg-gray-200">Save Settings</button>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={startRender}
            disabled={progress !== null}
            className="px-6 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
          >
            {progress !== null ? 'Rendering...' : 'Start Final Render'}
          </button>
        </div>
        {progress !== null && (
          <div className="mt-3">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${((progress ?? 0) * 100).toFixed(0)}%` }} />
            </div>
            <p className="text-xs text-gray-500 mt-1">{progressMsg || 'Processing...'}</p>
          </div>
        )}
      </div>

      {/* Render History */}
      {versions.length > 0 && (
        <div className="border-t pt-4 space-y-4">
          <h3 className="font-medium">Render History</h3>
          <div className="flex gap-2 flex-wrap">
            {versions.map((v, idx) => (
              <button
                type="button"
                key={v.job_id}
                onClick={() => v.has_file && setSelectedJobId(v.job_id)}
                disabled={!v.has_file}
                className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
                  selectedJobId === v.job_id
                    ? 'border-blue-400 bg-blue-50'
                    : v.has_file
                    ? 'border-gray-200 hover:bg-gray-50'
                    : 'border-gray-100 opacity-40 cursor-not-allowed'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs">#{versions.length - idx}</span>
                  {v.is_latest && <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">latest</span>}
                  <StatusBadge status={v.status} />
                </div>
                <p className="text-xs text-gray-400 mt-1">{new Date(v.created_at).toLocaleString()}</p>
                {v.output && <p className="text-xs text-gray-500">{(v.output as Record<string, unknown>).scene_count as number} scenes</p>}
                {v.error && <p className="text-xs text-red-500 truncate max-w-48">{v.error}</p>}
              </button>
            ))}
          </div>

          {selectedVersion && selectedVersion.has_file && (
            <div>
              <video
                key={selectedJobId}
                controls
                className="w-full max-w-2xl rounded-lg border"
                aria-label="Rendered video"
              >
                <source src={videoUrl} type="video/mp4" />
                <track kind="captions" />
              </video>
              <a
                href={videoUrl}
                download
                className="inline-block mt-2 px-4 py-2 bg-gray-100 rounded-lg text-sm hover:bg-gray-200"
              >
                Download
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
