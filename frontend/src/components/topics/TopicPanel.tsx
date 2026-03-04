import { useState, useEffect, useCallback } from 'react'
import client from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Topic, TopicCreate, WebSocketMessage } from '@/types'

interface Props {
  projectId: string
  lastMessage: WebSocketMessage | null
}

export function TopicPanel({ projectId, lastMessage }: Props) {
  const [topics, setTopics] = useState<Topic[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  const load = useCallback(async () => {
    const { data } = await client.get<Topic[]>(`/projects/${projectId}/topics`)
    setTopics(data)
  }, [projectId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (lastMessage?.event === 'job_completed' && lastMessage.job_type === 'generate_pitch') load()
  }, [lastMessage, load])

  const addTopic = async () => {
    if (!newTitle.trim()) return
    const body: TopicCreate = { title: newTitle.trim(), source: 'manual' }
    await client.post(`/projects/${projectId}/topics`, body)
    setNewTitle('')
    setShowAdd(false)
    load()
  }

  const updateStatus = async (topicId: string, status: 'SELECTED' | 'REJECTED') => {
    await client.patch(`/projects/${projectId}/topics/${topicId}`, { status })
    load()
  }

  const saveTitle = async (topicId: string) => {
    await client.patch(`/projects/${projectId}/topics/${topicId}`, { title: editTitle })
    setEditingId(null)
    load()
  }

  const generatePitch = async (topicId: string) => {
    await client.post(`/projects/${projectId}/topics/${topicId}/pitch`)
  }

  const deleteTopic = async (topicId: string) => {
    await client.delete(`/projects/${projectId}/topics/${topicId}`)
    load()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Topics</h2>
        <button onClick={() => setShowAdd(true)} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
          Add Topic
        </button>
      </div>

      {showAdd && (
        <div className="border rounded-lg p-4 bg-gray-50">
          <label htmlFor="new-topic" className="block text-sm font-medium mb-1">Topic Title</label>
          <input
            id="new-topic"
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addTopic()}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-2"
            placeholder="Enter topic title..."
            autoFocus
          />
          <div className="flex gap-2">
            <button onClick={addTopic} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm">Save</button>
            <button onClick={() => setShowAdd(false)} className="px-3 py-1.5 text-sm text-gray-600">Cancel</button>
          </div>
        </div>
      )}

      {topics.length === 0 ? (
        <p className="text-sm text-gray-500">No topics yet. Run research or add one manually.</p>
      ) : (
        <div className="grid gap-3">
          {topics.map(t => (
            <div key={t.id} className="border rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-gray-400">{t.id}</span>
                    <StatusBadge status={t.status} />
                    <span className="text-xs text-gray-400">{t.source}</span>
                  </div>
                  {editingId === t.id ? (
                    <div className="flex gap-2 items-center">
                      <input
                        value={editTitle}
                        onChange={e => setEditTitle(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && saveTitle(t.id)}
                        className="border rounded px-2 py-1 text-sm flex-1"
                        autoFocus
                        aria-label="Edit topic title"
                      />
                      <button onClick={() => saveTitle(t.id)} className="text-sm text-blue-600">Save</button>
                      <button onClick={() => setEditingId(null)} className="text-sm text-gray-500">Cancel</button>
                    </div>
                  ) : (
                    <h3
                      className="font-medium cursor-pointer hover:text-blue-600"
                      onClick={() => { setEditingId(t.id); setEditTitle(t.title) }}
                    >
                      {t.title}
                    </h3>
                  )}
                  {t.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {t.keywords.map((kw, i) => (
                        <span key={i} className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">{kw}</span>
                      ))}
                    </div>
                  )}
                  {t.score > 0 && <p className="text-xs text-gray-400 mt-1">Score: {t.score.toFixed(2)}</p>}
                </div>
                <div className="flex gap-1 ml-3">
                  {t.status === 'PENDING' && (
                    <>
                      <button onClick={() => updateStatus(t.id, 'SELECTED')} className="px-2 py-1 text-xs bg-green-50 text-green-700 rounded hover:bg-green-100">Select</button>
                      <button onClick={() => updateStatus(t.id, 'REJECTED')} className="px-2 py-1 text-xs bg-red-50 text-red-700 rounded hover:bg-red-100">Reject</button>
                    </>
                  )}
                  <button onClick={() => generatePitch(t.id)} className="px-2 py-1 text-xs bg-purple-50 text-purple-700 rounded hover:bg-purple-100">Pitch</button>
                  <button onClick={() => deleteTopic(t.id)} className="px-2 py-1 text-xs text-gray-400 hover:text-red-500">✕</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
