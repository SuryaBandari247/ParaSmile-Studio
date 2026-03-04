import { useState, useEffect, useCallback } from 'react'
import * as scriptsApi from '@/api/scripts'
import client from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { ScriptVersion, DiffResult, Topic } from '@/types'

interface Props {
  projectId: string
}

export function ScriptPanel({ projectId }: Props) {
  const [versions, setVersions] = useState<ScriptVersion[]>([])
  const [selected, setSelected] = useState<ScriptVersion | null>(null)
  const [diff, setDiff] = useState<DiffResult | null>(null)
  const [diffV1, setDiffV1] = useState<number | ''>('')
  const [diffV2, setDiffV2] = useState<number | ''>('')
  const [editingScene, setEditingScene] = useState<number | null>(null)

  // Create form state
  const [showCreate, setShowCreate] = useState(false)
  const [topics, setTopics] = useState<Topic[]>([])
  const [newTitle, setNewTitle] = useState('')
  const [newTopicId, setNewTopicId] = useState('')
  const [rawText, setRawText] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [showPaste, setShowPaste] = useState(false)
  const [pasteJson, setPasteJson] = useState('')
  const [pasteError, setPasteError] = useState<string | null>(null)
  const [pasting, setPasting] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichError, setEnrichError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const v = await scriptsApi.listVersions(projectId)
    setVersions(v)
  }, [projectId])

  const loadTopics = useCallback(async () => {
    const { data } = await client.get<Topic[]>(`/projects/${projectId}/topics`)
    setTopics(data)
  }, [projectId])

  useEffect(() => { load() }, [load])

  const selectVersion = async (v: ScriptVersion) => {
    const full = await scriptsApi.getVersion(projectId, v.id)
    setSelected(full)
    setDiff(null)
  }

  const openCreateForm = async () => {
    await loadTopics()
    setShowCreate(true)
    setNewTitle('')
    setNewTopicId('')
    setRawText('')
    setCreateError(null)
  }

  const handleGenerate = async () => {
    if (!newTitle.trim()) { setCreateError('Title is required'); return }
    if (!newTopicId) { setCreateError('Select a topic'); return }
    if (!rawText.trim()) { setCreateError('Paste your script text'); return }
    setCreating(true)
    setCreateError(null)
    try {
      const created = await scriptsApi.generateFromRaw(projectId, {
        topic_id: newTopicId,
        title: newTitle.trim(),
        raw_text: rawText.trim(),
      })
      setShowCreate(false)
      await load()
      setSelected(created)
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : 'AI generation failed. Check that OPENAI_API_KEY is set.')
    } finally {
      setCreating(false)
    }
  }

  const handleImportJson = async () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async () => {
      const file = input.files?.[0]
      if (!file) return
      setImporting(true)
      setImportError(null)
      try {
        const text = await file.text()
        const json = JSON.parse(text)
        if (!json.scenes || !Array.isArray(json.scenes)) {
          throw new Error('JSON must contain a "scenes" array')
        }
        const imported = await scriptsApi.importJson(projectId, {
          script_json: json,
          title: json.title || file.name.replace('.json', ''),
        })
        await load()
        setSelected(imported)
      } catch (e) {
        setImportError(e instanceof Error ? e.message : 'Failed to import JSON')
      } finally {
        setImporting(false)
      }
    }
    input.click()
  }

  const handlePasteImport = async () => {
    if (!pasteJson.trim()) { setPasteError('Paste your JSON first'); return }
    setPasting(true)
    setPasteError(null)
    try {
      const json = JSON.parse(pasteJson)
      if (!json.scenes || !Array.isArray(json.scenes)) {
        throw new Error('JSON must contain a "scenes" array')
      }
      const imported = await scriptsApi.importJson(projectId, {
        script_json: json,
        title: json.title || 'Pasted Script',
      })
      await load()
      setSelected(imported)
      setShowPaste(false)
      setPasteJson('')
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : 'Invalid JSON')
    } finally {
      setPasting(false)
    }
  }

  const handleFinalize = async (versionId: number) => {
    await scriptsApi.finalize(projectId, versionId)
    load()
    if (selected?.id === versionId) {
      const updated = await scriptsApi.getVersion(projectId, versionId)
      setSelected(updated)
    }
  }

  const handleEnrichKeywords = async (versionId: number) => {
    setEnriching(true)
    setEnrichError(null)
    try {
      const updated = await scriptsApi.enrichKeywords(projectId, versionId)
      if (selected?.id === versionId) setSelected(updated)
      await load()
    } catch (e) {
      setEnrichError(e instanceof Error ? e.message : 'Keyword enrichment failed. Check that OPENAI_API_KEY is set.')
    } finally {
      setEnriching(false)
    }
  }

  const handleDiff = async () => {
    if (diffV1 === '' || diffV2 === '') return
    const d = await scriptsApi.getDiff(projectId, diffV1, diffV2)
    setDiff(d)
  }

  const updateSceneNarration = async (sceneIdx: number, text: string) => {
    if (!selected || selected.is_finalized) return
    const sj = { ...selected.script_json } as Record<string, unknown>
    const sc = [...(sj.scenes as Array<Record<string, unknown>> || [])]
    sc[sceneIdx] = { ...sc[sceneIdx], narration: text, narration_text: text }
    sj.scenes = sc
    const updated = await scriptsApi.updateVersion(projectId, selected.id, { script_json: sj })
    setSelected(updated)
    setEditingScene(null)
  }

  const selectedScenes = selected
    ? ((selected.script_json as Record<string, unknown>).scenes as Array<Record<string, unknown>> || [])
    : []

  const getSceneNarration = (scene: Record<string, unknown>) =>
    (scene.narration_text as string) || (scene.narration as string) || ''

  const deleteScene = async (sceneIdx: number) => {
    if (!selected || selected.is_finalized) return
    const sj = { ...selected.script_json } as Record<string, unknown>
    const sc = [...(sj.scenes as Array<Record<string, unknown>> || [])]
    sc.splice(sceneIdx, 1)
    // Re-number remaining scenes
    sc.forEach((s, i) => { s.scene_number = i + 1 })
    sj.scenes = sc
    const updated = await scriptsApi.updateVersion(projectId, selected.id, { script_json: sj })
    setSelected(updated)
    setEditingScene(null)
  }

  const handleDeleteAll = async () => {
    if (!confirm('Delete all script versions? This cannot be undone.')) return
    await scriptsApi.deleteAll(projectId)
    setSelected(null)
    setVersions([])
    load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Script Versions</h2>
        <div className="flex items-center gap-2">
          {versions.length > 0 && (
            <button type="button" onClick={handleDeleteAll} className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-sm hover:bg-red-100">
              Delete All
            </button>
          )}
          <button type="button" onClick={openCreateForm} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
            New Script
          </button>
          <button
            type="button"
            onClick={handleImportJson}
            disabled={importing}
            className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
          >
            {importing ? <><span className="animate-spin text-xs">⏳</span> Importing...</> : '📂 Import JSON'}
          </button>
          <button
            type="button"
            onClick={() => { setShowPaste(!showPaste); setPasteError(null); setShowCreate(false) }}
            className="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700"
          >
            📋 Paste JSON
          </button>
        </div>
      </div>

      {importError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{importError}</div>}

      {showPaste && (
        <div className="border rounded-lg p-4 bg-gray-50 space-y-3">
          <h3 className="font-medium text-sm">Paste Script JSON</h3>
          <p className="text-xs text-gray-500">Paste your complete script JSON below. It will be imported as-is and auto-finalized — no LLM processing.</p>
          <textarea
            value={pasteJson}
            onChange={e => setPasteJson(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm font-mono bg-white"
            rows={14}
            placeholder='{"title": "My Video", "scenes": [...]}'
            aria-label="Paste script JSON"
          />
          {pasteError && <p className="text-sm text-red-600">{pasteError}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handlePasteImport}
              disabled={pasting}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
            >
              {pasting ? <><span className="animate-spin text-xs">⏳</span> Importing...</> : 'Import & Finalize'}
            </button>
            <button type="button" onClick={() => { setShowPaste(false); setPasteJson('') }} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="border rounded-lg p-4 bg-gray-50 space-y-4">
          <h3 className="font-medium text-sm">Generate Script from Raw Text</h3>
          <p className="text-xs text-gray-500">Paste your script text below. AI will automatically split it into scenes with visual types.</p>
          <div>
            <label htmlFor="script-title" className="block text-sm font-medium mb-1">Title</label>
            <input
              id="script-title"
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. Why Rust is Taking Over Systems Programming"
            />
          </div>
          <div>
            <label htmlFor="script-topic" className="block text-sm font-medium mb-1">Topic</label>
            {topics.length === 0 ? (
              <p className="text-sm text-gray-500">No topics found. Add a topic first in the Topic stage.</p>
            ) : (
              <select id="script-topic" value={newTopicId} onChange={e => setNewTopicId(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm">
                <option value="">Select a topic...</option>
                {topics.map(t => (
                  <option key={t.id} value={t.id}>{t.title} ({t.id})</option>
                ))}
              </select>
            )}
          </div>
          <div>
            <label htmlFor="raw-text" className="block text-sm font-medium mb-1">Raw Script Text</label>
            <textarea
              id="raw-text"
              value={rawText}
              onChange={e => setRawText(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm font-mono"
              rows={12}
              placeholder="Paste your full script text here. The AI will break it into scenes, assign visual types (charts, code snippets, text overlays), and preserve all narration content..."
            />
            <p className="text-xs text-gray-400 mt-1">{rawText.split(/\s+/).filter(Boolean).length} words</p>
          </div>
          {createError && <p className="text-sm text-red-600">{createError}</p>}
          <div className="flex gap-2">
            <button type="button" onClick={handleGenerate} disabled={creating} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2">
              {creating && <span className="animate-spin text-xs">⏳</span>}
              {creating ? 'Generating scenes...' : 'Generate Scenes with AI'}
            </button>
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex gap-6">
        <div className="w-64 space-y-2">
          {versions.length === 0 ? (
            <p className="text-sm text-gray-500">No script versions yet.</p>
          ) : versions.map(v => (
            <button
              type="button"
              key={v.id}
              onClick={() => selectVersion(v)}
              className={`w-full text-left border rounded-lg p-3 text-sm transition-colors ${selected?.id === v.id ? 'border-blue-300 bg-blue-50' : 'hover:bg-gray-50'}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">v{v.version}</span>
                {v.is_finalized && <StatusBadge status="COMPLETED" />}
              </div>
              <p className="text-xs text-gray-500 truncate">{v.title}</p>
            </button>
          ))}
        </div>

        <div className="flex-1">
          {selected ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">{selected.title} (v{selected.version})</h3>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleEnrichKeywords(selected.id)}
                    disabled={enriching}
                    className="px-3 py-1.5 bg-violet-600 text-white rounded-lg text-sm hover:bg-violet-700 disabled:opacity-50 flex items-center gap-2"
                  >
                    {enriching ? <><span className="animate-spin text-xs">⏳</span> Researching...</> : '🔬 Research Keywords'}
                  </button>
                  {!selected.is_finalized && (
                    <button type="button" onClick={() => handleFinalize(selected.id)} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
                      Finalize
                    </button>
                  )}
                </div>
              </div>
              {enrichError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{enrichError}</div>}
              <div className="space-y-3">
                {selectedScenes.map((scene, idx) => (
                  <div key={idx} className="border rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono text-gray-400">Scene {idx + 1}</span>
                      <div className="flex items-center gap-2">
                        {(scene.emotion as string) && (scene.emotion as string) !== 'neutral' && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">{scene.emotion as string}</span>
                        )}
                        <span className="text-xs text-gray-400">{(scene.visual_type as string) || (scene.visual_instruction as Record<string, unknown>)?.type as string || ''}</span>
                        {!selected.is_finalized && (
                          <button type="button" onClick={() => deleteScene(idx)} className="text-xs text-gray-400 hover:text-red-500" aria-label={`Delete scene ${idx + 1}`}>✕</button>
                        )}
                      </div>
                    </div>
                    {editingScene === idx && !selected.is_finalized ? (
                      <div>
                        <textarea
                          defaultValue={getSceneNarration(scene)}
                          className="w-full border rounded px-2 py-1 text-sm"
                          rows={3}
                          aria-label={`Narration for scene ${idx + 1}`}
                          onKeyDown={e => {
                            if (e.key === 'Enter' && e.metaKey) {
                              updateSceneNarration(idx, (e.target as HTMLTextAreaElement).value)
                            }
                          }}
                          id={`scene-narration-${idx}`}
                        />
                        <div className="flex gap-2 mt-1">
                          <button type="button" onClick={() => { const el = document.getElementById(`scene-narration-${idx}`) as HTMLTextAreaElement; updateSceneNarration(idx, el.value) }} className="text-xs text-blue-600">Save</button>
                          <button type="button" onClick={() => setEditingScene(null)} className="text-xs text-gray-500">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <p
                        className={`text-sm ${selected.is_finalized ? '' : 'cursor-pointer hover:bg-gray-50 rounded p-1'}`}
                        onClick={() => !selected.is_finalized && setEditingScene(idx)}
                      >
                        {getSceneNarration(scene) || <span className="text-gray-400 italic">No narration</span>}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Select a version to view.</p>
          )}
        </div>
      </div>

      {versions.length >= 2 && (
        <div className="border-t pt-4">
          <h3 className="font-medium mb-2">Compare Versions</h3>
          <div className="flex items-center gap-2">
            <select value={diffV1} onChange={e => setDiffV1(e.target.value ? Number(e.target.value) : '')} className="border rounded px-2 py-1 text-sm" aria-label="Version A">
              <option value="">Version A</option>
              {versions.map(v => <option key={v.id} value={v.id}>v{v.version}</option>)}
            </select>
            <span className="text-gray-400">vs</span>
            <select value={diffV2} onChange={e => setDiffV2(e.target.value ? Number(e.target.value) : '')} className="border rounded px-2 py-1 text-sm" aria-label="Version B">
              <option value="">Version B</option>
              {versions.map(v => <option key={v.id} value={v.id}>v{v.version}</option>)}
            </select>
            <button type="button" onClick={handleDiff} className="px-3 py-1 bg-gray-100 rounded text-sm hover:bg-gray-200">Diff</button>
          </div>
          {diff && (
            <div className="mt-3 bg-gray-50 border rounded-lg p-4 text-xs font-mono overflow-auto max-h-64">
              {diff.changes.map((c, i) => (
                <div key={i} className={c.type === 'added' ? 'text-green-700' : c.type === 'removed' ? 'text-red-700' : 'text-gray-500'}>
                  {c.type === 'added' ? '+ ' : c.type === 'removed' ? '- ' : '  '}{c.content}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
