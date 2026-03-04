import { useState, useEffect, useCallback, useRef } from 'react'
import * as audioApi from '@/api/audio'
import * as scriptsApi from '@/api/scripts'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { AudioSegment, ScriptVersion, WebSocketMessage, VoiceParams, PipelineStage } from '@/types'

const EMOTIONS = [
  'neutral', 'happy', 'excited', 'confident', 'curious', 'calm',
  'serious', 'surprised', 'empathetic', 'sarcastic', 'worried',
  'frustrated', 'satisfied', 'proud', 'determined', 'nostalgic',
]

const GLOBAL_DEFAULT_SPEED = 0.9

const DEFAULT_PARAMS: VoiceParams = {
  speed: GLOBAL_DEFAULT_SPEED, temperature: 0.6, top_p: 0.7,
  repetition_penalty: 1.4, emotion: 'neutral', emphasis: 'none',
}

interface Props {
  projectId: string
  lastMessage: WebSocketMessage | null
  onStageChange?: (stage: PipelineStage) => void
}

export function AudioPanel({ projectId, lastMessage, onStageChange }: Props) {
  const [segments, setSegments] = useState<AudioSegment[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [finalizedScripts, setFinalizedScripts] = useState<ScriptVersion[]>([])
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)
  const [audioCacheBust, setAudioCacheBust] = useState(Date.now().toString())
  const [synthError, setSynthError] = useState<string | null>(null)
  const [synthesizing, setSynthesizing] = useState<Set<number>>(new Set())
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [globalSpeed, setGlobalSpeed] = useState(GLOBAL_DEFAULT_SPEED)
  const [sceneSpeedOverrides, setSceneSpeedOverrides] = useState<Set<number>>(new Set())
  const [finalizing, setFinalizing] = useState(false)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    const s = await audioApi.listSegments(projectId)
    setSegments(s)
  }, [projectId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    scriptsApi.listVersions(projectId).then(all => {
      setFinalizedScripts(all.filter(s => s.is_finalized))
    }).catch(() => {})
  }, [projectId])

  const handleGenerateTimeline = async (scriptVersionId: number) => {
    setGenerating(true)
    setGenError(null)
    try {
      await audioApi.generateTimeline(projectId, scriptVersionId)
      await load()
    } catch (e) {
      setGenError(e instanceof Error ? e.message : 'Failed to generate timeline')
    } finally { setGenerating(false) }
  }

  useEffect(() => {
    if (lastMessage?.event === 'job_completed' && lastMessage.job_type === 'synthesize_audio') {
      load()
      setAudioCacheBust(Date.now().toString())
    }
  }, [lastMessage, load])

  const handleSynthesize = async (segmentId: number) => {
    setSynthError(null)
    setSynthesizing(prev => new Set(prev).add(segmentId))
    try {
      await audioApi.synthesize(projectId, segmentId)
      const poll = setInterval(async () => {
        const segs = await audioApi.listSegments(projectId)
        const seg = segs.find(s => s.id === segmentId)
        if (seg && !['PENDING','RUNNING','QUEUED'].includes(seg.status)) {
          clearInterval(poll)
          setSynthesizing(prev => { const s = new Set(prev); s.delete(segmentId); return s })
          setSegments(segs)
          setAudioCacheBust(Date.now().toString())
        }
      }, 3000)
      setTimeout(() => setSynthesizing(prev => { const s = new Set(prev); s.delete(segmentId); return s }), 300000)
    } catch (e) {
      setSynthError(`Segment ${segmentId}: ${e instanceof Error ? e.message : 'Synthesis failed'}`)
      setSynthesizing(prev => { const s = new Set(prev); s.delete(segmentId); return s })
    }
  }

  const handleSynthesizeAll = async () => {
    setSynthError(null)
    const pending = segments.filter(s => s.status !== 'SYNTHESIZED' && s.status !== 'UPLOADED')
    if (pending.length === 0) return
    const ids = new Set(pending.map(s => s.id))
    setSynthesizing(ids)
    // Fire all synthesis requests in parallel — backend queue handles concurrency
    await Promise.all(pending.map(seg => audioApi.synthesize(projectId, seg.id).catch(() => {})))
    // Poll for completion
    const poll = setInterval(async () => {
      const segs = await audioApi.listSegments(projectId)
      setSegments(segs)
      const stillBusy = segs.filter(s => ids.has(s.id) && ['PENDING','RUNNING','QUEUED'].includes(s.status))
      if (stillBusy.length === 0) {
        clearInterval(poll)
        setSynthesizing(new Set())
        setAudioCacheBust(Date.now().toString())
      }
    }, 3000)
    setTimeout(() => setSynthesizing(new Set()), 300000)
  }

  const handleDeleteAll = async () => {
    if (!confirm('Delete all audio segments?')) return
    await audioApi.deleteAllSegments(projectId)
    setSegments([])
    setSynthesizing(new Set())
  }

  const handleFinalizeAudio = async () => {
    setFinalizing(true)
    setFinalizeError(null)
    try {
      await audioApi.finalizeAudio(projectId)
      if (onStageChange) onStageChange('VISUAL')
    } catch (e) {
      setFinalizeError(e instanceof Error ? e.message : 'Finalize failed')
    } finally {
      setFinalizing(false)
    }
  }

  const handleUploadMaster = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError(null)
    setSynthError(null)
    try {
      await audioApi.uploadMasterAudio(projectId, file)
      // Poll for completion — segments will transition to UPLOADED
      const poll = setInterval(async () => {
        const segs = await audioApi.listSegments(projectId)
        setSegments(segs)
        const uploaded = segs.filter(s => s.status === 'UPLOADED').length
        if (uploaded > 0) {
          clearInterval(poll)
          setUploading(false)
          setAudioCacheBust(Date.now().toString())
        }
      }, 3000)
      // Safety timeout: stop polling after 5 minutes
      setTimeout(() => { setUploading(false) }, 300000)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
    // Reset file input so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleGlobalSpeedChange = (newSpeed: number) => {
    setGlobalSpeed(newSpeed)
  }

  const applyGlobalSpeed = async () => {
    // Push global speed to all segments that don't have a per-scene override
    for (const seg of segments) {
      if (!sceneSpeedOverrides.has(seg.id)) {
        await audioApi.updateSegment(projectId, seg.id, {
          voice_params: { ...DEFAULT_PARAMS, ...(seg.voice_params || {}), speed: globalSpeed },
        } as unknown as Partial<AudioSegment>)
      }
    }
    load()
  }

  const handleUpdateParamWithOverride = async (id: number, key: string, value: number | string) => {
    if (key === 'speed') {
      setSceneSpeedOverrides(prev => new Set(prev).add(id))
    }
    await handleUpdateParam(id, key, value)
  }

  const handleResetToGlobal = async (id: number) => {
    setSceneSpeedOverrides(prev => { const s = new Set(prev); s.delete(id); return s })
    await handleUpdateParam(id, 'speed', globalSpeed)
  }

  const handleDelete = async (id: number) => {
    await audioApi.deleteSegment(projectId, id)
    load()
  }

  const handlePause = async (id: number) => {
    await audioApi.insertPause(projectId, id)
    load()
  }

  const handleUpdateText = async (id: number, text: string) => {
    await audioApi.updateSegment(projectId, id, { narration_text: text } as Partial<AudioSegment>)
    setEditingId(null)
    load()
  }

  const handleUpdateParam = async (id: number, key: string, value: number | string) => {
    const seg = segments.find(s => s.id === id)
    const params = { ...DEFAULT_PARAMS, ...(seg?.voice_params || {}), [key]: value }
    await audioApi.updateSegment(projectId, id, { voice_params: params } as unknown as Partial<AudioSegment>)
    load()
  }

  const synthesizedCount = segments.filter(s => s.status === 'SYNTHESIZED' || s.status === 'UPLOADED').length
  const allSynthesized = segments.length > 0 && synthesizedCount === segments.length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">Audio Timeline</h2>
          {segments.length > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">{synthesizedCount}/{segments.length} synthesized</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {segments.length > 0 && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".wav,.mp3,.m4a,.flac,.ogg,.webm"
                onChange={handleUploadMaster}
                className="hidden"
                aria-label="Upload master audio recording"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="px-3 py-1.5 bg-teal-600 text-white rounded-lg text-sm hover:bg-teal-700 disabled:opacity-50 flex items-center gap-2"
              >
                {uploading ? <><span className="animate-spin text-xs">⏳</span> Processing...</> : '🎙 Upload Recording'}
              </button>
              <button type="button" onClick={handleDeleteAll} className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100">Delete All</button>
              {!allSynthesized && (
                <button type="button" onClick={handleSynthesizeAll} disabled={synthesizing.size > 0} className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2">
                  {synthesizing.size > 0 ? <><span className="animate-spin text-xs">⏳</span> Synthesizing {synthesizing.size}...</> : 'Synthesize All'}
                </button>
              )}
              {allSynthesized && (
                <button type="button" onClick={handleFinalizeAudio} disabled={finalizing} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">
                  {finalizing ? '⏳ Finalizing...' : '✓ Finalize Audio'}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {synthError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{synthError}</div>}
      {uploadError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{uploadError}</div>}
      {finalizeError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{finalizeError}</div>}
      {uploading && <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 text-sm text-teal-700">🎙 Transcribing and splitting your recording... This may take a minute.</div>}

      {/* Global speed control */}
      {segments.length > 0 && (
        <div className="flex items-center gap-4 border rounded-lg px-4 py-2 bg-gray-50">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <span className="font-medium">Global Speed</span>
            <input type="range" min="0.5" max="2.0" step="0.1" value={globalSpeed} onChange={e => handleGlobalSpeedChange(parseFloat(e.target.value))} className="w-32" />
            <span className="font-mono text-sm w-12">{globalSpeed.toFixed(1)}×</span>
          </label>
          <button type="button" onClick={applyGlobalSpeed} className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700">Apply to All</button>
          <span className="text-xs text-gray-400">Per-scene overrides take priority</span>
          {sceneSpeedOverrides.size > 0 && (
            <span className="text-xs text-amber-600">{sceneSpeedOverrides.size} scene{sceneSpeedOverrides.size > 1 ? 's' : ''} overridden</span>
          )}
        </div>
      )}

      {/* Empty state */}
      {segments.length === 0 ? (
        <div className="space-y-3">
          {finalizedScripts.length === 0 ? (
            <p className="text-sm text-gray-500">No finalized scripts. Finalize a script first.</p>
          ) : (
            <div className="border rounded-lg p-4 bg-gray-50">
              <p className="text-sm font-medium mb-3">Generate audio timeline from a finalized script:</p>
              {finalizedScripts.map(s => {
                const cnt = ((s.script_json as Record<string, unknown>)?.scenes as unknown[])?.length ?? '?'
                return (
                  <div key={s.id} className="flex items-center justify-between border rounded-lg p-3 bg-white mb-2">
                    <span className="text-sm font-medium">{s.title} <span className="text-xs text-gray-400">v{s.version} · {cnt} scenes</span></span>
                    <button type="button" onClick={() => handleGenerateTimeline(s.id)} disabled={generating} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                      {generating ? 'Generating...' : 'Generate Timeline'}
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
          {finalizedScripts.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-gray-500 hover:text-gray-700">Regenerate from a different script version</summary>
              <div className="mt-2 space-y-2">
                {finalizedScripts.map(s => (
                  <div key={s.id} className="flex items-center justify-between border rounded-lg p-3 bg-gray-50">
                    <span className="text-sm">{s.title} <span className="text-xs text-gray-400">v{s.version}</span></span>
                    <button type="button" onClick={() => handleGenerateTimeline(s.id)} disabled={generating} className="px-3 py-1.5 bg-gray-600 text-white rounded-lg text-xs hover:bg-gray-700 disabled:opacity-50">
                      {generating ? 'Generating...' : 'Regenerate'}
                    </button>
                  </div>
                ))}
              </div>
            </details>
          )}

          {/* Segment cards */}
          <div className="space-y-3">
            {segments.map(seg => {
              const vp = { ...DEFAULT_PARAMS, ...(seg.voice_params || {}) }
              const isSynth = seg.status === 'SYNTHESIZED' || seg.status === 'UPLOADED'
              const isOpen = expandedId === seg.id
              const isBusy = synthesizing.has(seg.id)

              return (
                <div key={seg.id} className={`border rounded-lg overflow-hidden ${isSynth ? 'border-green-200' : 'border-gray-200'}`}>
                  {/* Compact header row */}
                  <div
                    className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50/50"
                    onClick={() => setExpandedId(isOpen ? null : seg.id)}
                  >
                    <span className="text-xs font-mono text-gray-400 w-10 shrink-0">#{seg.scene_number}</span>

                    {/* Emotion badge */}
                    <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${
                      vp.emotion !== 'neutral' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'
                    }`}>{vp.emotion}</span>

                    <p className="text-sm text-gray-700 truncate flex-1">{seg.narration_text}</p>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono" title="Speed">{vp.speed.toFixed(1)}×</span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-mono" title="Temperature">T{vp.temperature.toFixed(1)}</span>
                      <StatusBadge status={seg.status} />
                      {isSynth && seg.audio_file_path && (
                        <audio controls src={audioApi.getPreviewUrl(projectId, seg.id, audioCacheBust)} className="h-8" aria-label={`Preview segment ${seg.scene_number}`} onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>
                          <track kind="captions" />
                        </audio>
                      )}
                      <span className="text-gray-400 text-xs">{isOpen ? '▲' : '▼'}</span>
                    </div>
                  </div>

                  {/* Expanded controls */}
                  {isOpen && (
                    <div className="border-t px-4 py-4 bg-white space-y-4">
                      {/* Narration text */}
                      {editingId === seg.id ? (
                        <div>
                          <textarea defaultValue={seg.narration_text} className="w-full border rounded px-2 py-1 text-sm" rows={3} id={`seg-text-${seg.id}`} aria-label={`Narration for segment ${seg.scene_number}`} />
                          <div className="flex gap-2 mt-1">
                            <button type="button" onClick={() => { const el = document.getElementById(`seg-text-${seg.id}`) as HTMLTextAreaElement; handleUpdateText(seg.id, el.value) }} className="text-xs text-blue-600 hover:underline">Save</button>
                            <button type="button" onClick={() => setEditingId(null)} className="text-xs text-gray-500 hover:underline">Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-gray-700 cursor-pointer hover:bg-gray-50 rounded p-1" onClick={() => setEditingId(seg.id)}>
                          {seg.narration_text} <span className="text-xs text-gray-400">(click to edit)</span>
                        </p>
                      )}

                      {/* Timing info */}
                      <div className="text-xs text-gray-500">{seg.start_time} → {seg.end_time} · v{seg.version}</div>

                      {/* Voice controls grid */}
                      <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                        {/* Emotion */}
                        <label className="flex items-center gap-2 text-xs text-gray-600">
                          <span className="w-28">Emotion</span>
                          <select
                            value={vp.emotion}
                            onChange={e => handleUpdateParam(seg.id, 'emotion', e.target.value)}
                            className="border rounded px-2 py-1 text-xs flex-1"
                          >
                            {EMOTIONS.map(e => <option key={e} value={e}>{e}</option>)}
                          </select>
                        </label>

                        {/* Speed */}
                        <label className="flex items-center gap-2 text-xs text-gray-600">
                          <span className="w-28">Speed</span>
                          <input type="range" min="0.5" max="2.0" step="0.1" value={vp.speed} onChange={e => handleUpdateParamWithOverride(seg.id, 'speed', parseFloat(e.target.value))} className="w-24" />
                          <span className="font-mono w-10">{vp.speed.toFixed(1)}×</span>
                          {sceneSpeedOverrides.has(seg.id) ? (
                            <button type="button" onClick={() => handleResetToGlobal(seg.id)} className="text-xs text-amber-600 hover:underline" title="Reset to global speed">↺ reset</button>
                          ) : (
                            <span className="text-xs text-gray-400">global</span>
                          )}
                        </label>

                        {/* Temperature */}
                        <label className="flex items-center gap-2 text-xs text-gray-600" title="Higher = more expressive/varied, Lower = more stable/consistent">
                          <span className="w-28">Temperature</span>
                          <input type="range" min="0.1" max="1.0" step="0.1" value={vp.temperature} onChange={e => handleUpdateParam(seg.id, 'temperature', parseFloat(e.target.value))} className="w-24" />
                          <span className="font-mono w-10">{vp.temperature.toFixed(1)}</span>
                        </label>

                        {/* Top P */}
                        <label className="flex items-center gap-2 text-xs text-gray-600" title="Nucleus sampling — lower = tighter/fewer artifacts">
                          <span className="w-28">Top P</span>
                          <input type="range" min="0.1" max="1.0" step="0.1" value={vp.top_p} onChange={e => handleUpdateParam(seg.id, 'top_p', parseFloat(e.target.value))} className="w-24" />
                          <span className="font-mono w-10">{vp.top_p.toFixed(1)}</span>
                        </label>

                        {/* Repetition Penalty */}
                        <label className="flex items-center gap-2 text-xs text-gray-600" title="Higher = fewer repeated words/phrases">
                          <span className="w-28">Rep. Penalty</span>
                          <input type="range" min="0.9" max="2.0" step="0.1" value={vp.repetition_penalty} onChange={e => handleUpdateParam(seg.id, 'repetition_penalty', parseFloat(e.target.value))} className="w-24" />
                          <span className="font-mono w-10">{vp.repetition_penalty.toFixed(1)}</span>
                        </label>
                      </div>

                      {isSynth && <p className="text-xs text-gray-400 italic">Change parameters above, then re-synthesize to hear the difference.</p>}

                      {/* Actions */}
                      <div className="flex items-center gap-2 pt-1">
                        <button type="button" onClick={() => handleSynthesize(seg.id)} disabled={isBusy} className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                          {isBusy ? '⏳ Synthesizing...' : isSynth ? '↻ Re-synthesize' : '▶ Synthesize'}
                        </button>
                        <button type="button" onClick={() => handlePause(seg.id)} className="px-3 py-1.5 text-xs bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">+ Pause After</button>
                        <button type="button" onClick={() => handleDelete(seg.id)} className="px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 rounded-lg" aria-label={`Delete segment ${seg.scene_number}`}>Delete</button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
