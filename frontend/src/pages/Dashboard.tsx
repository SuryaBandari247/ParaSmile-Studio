import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { listProjects, createProject, deleteProject } from '@/api/projects'
import { getRecentTopics, quickStart, researchAllSources } from '@/api/quickstart'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { Project, Topic } from '@/types'

type SortKey = 'updated_at' | 'created_at' | 'title'

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [recentTopics, setRecentTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [ownTopic, setOwnTopic] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('updated_at')
  const [filterStatus, setFilterStatus] = useState<string>('ALL')
  const [researchLoading, setResearchLoading] = useState(false)
  const [researchError, setResearchError] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      const [p, t] = await Promise.all([listProjects(), getRecentTopics()])
      setProjects(p)
      setRecentTopics(t)
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!title.trim()) return
    const p = await createProject({ title: title.trim(), description: description.trim() })
    setShowCreate(false)
    setTitle('')
    setDescription('')
    navigate(`/projects/${p.id}`)
  }

  const handleDelete = async (id: string) => {
    await deleteProject(id)
    setProjects(prev => prev.filter(p => p.id !== id))
  }

  const handleSearchTrends = async () => {
    setResearchLoading(true)
    setResearchError(null)
    try {
      const result = await researchAllSources()
      navigate(`/projects/${result.project_id}`)
    } catch (e) {
      setResearchError(e instanceof Error ? e.message : 'Research failed — check API keys and try again')
      setResearchLoading(false)
    }
  }

  const handleOwnTopic = async () => {
    if (!ownTopic.trim()) return
    const result = await quickStart({ title: ownTopic.trim(), topic: ownTopic.trim() })
    const projectId = (result.project as Record<string, string>).id
    navigate(`/projects/${projectId}`)
  }

  const handlePickTopic = async (topic: Topic) => {
    navigate(`/projects/${topic.project_id}`)
  }

  const filtered = projects
    .filter(p => filterStatus === 'ALL' || p.status === filterStatus)
    .sort((a, b) => {
      if (sortBy === 'title') return a.title.localeCompare(b.title)
      return b[sortBy].localeCompare(a[sortBy])
    })

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Production Studio</h1>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <button
          onClick={handleSearchTrends}
          disabled={researchLoading}
          className="border-2 border-dashed border-blue-300 rounded-xl p-6 text-left hover:bg-blue-50 hover:border-blue-400 transition-colors disabled:opacity-50"
        >
          <span className="text-2xl mb-2 block">🔍</span>
          <span className="font-medium text-gray-900 block">Search Trends</span>
          <span className="text-sm text-gray-500">
            {researchLoading ? 'Searching all sources...' : 'Run all research sources and find trending topics'}
          </span>
          {researchLoading && <span className="animate-spin inline-block mt-2">⏳</span>}
          {researchError && <span className="text-sm text-red-600 block mt-2">{researchError}</span>}
        </button>

        <div className="border-2 border-dashed border-green-300 rounded-xl p-6">
          <span className="text-2xl mb-2 block">💡</span>
          <span className="font-medium text-gray-900 block mb-2">I Have a Topic</span>
          <div className="flex gap-2">
            <input
              value={ownTopic}
              onChange={e => setOwnTopic(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleOwnTopic()}
              className="flex-1 border rounded-lg px-3 py-1.5 text-sm"
              placeholder="e.g. Rust vs Go performance"
              aria-label="Enter your own topic"
            />
            <button
              onClick={handleOwnTopic}
              disabled={!ownTopic.trim()}
              className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
            >
              Go
            </button>
          </div>
        </div>

        <button
          onClick={() => setShowCreate(true)}
          className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-left hover:bg-gray-50 hover:border-gray-400 transition-colors"
        >
          <span className="text-2xl mb-2 block">📁</span>
          <span className="font-medium text-gray-900 block">New Empty Project</span>
          <span className="text-sm text-gray-500">Create a blank project and configure manually</span>
        </button>
      </div>

      {/* Recent Topics (History) */}
      {recentTopics.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-medium text-gray-900 mb-3">Recent Topics</h2>
          <div className="flex flex-wrap gap-2">
            {recentTopics.map(t => (
              <button
                key={t.id}
                onClick={() => handlePickTopic(t)}
                className="border rounded-lg px-3 py-2 text-sm hover:bg-blue-50 hover:border-blue-300 transition-colors text-left"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-gray-400">{t.id}</span>
                  <StatusBadge status={t.status} />
                </div>
                <span className="block font-medium text-gray-800 mt-0.5">{t.title}</span>
                <span className="text-xs text-gray-400">{t.source}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Projects List */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium text-gray-900">Projects</h2>
        <div className="flex gap-3">
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm"
            aria-label="Filter by status"
          >
            <option value="ALL">All statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="REVIEW">Review</option>
            <option value="RENDERED">Rendered</option>
            <option value="PUBLISHED">Published</option>
          </select>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as SortKey)}
            className="border rounded-lg px-3 py-1.5 text-sm"
            aria-label="Sort by"
          >
            <option value="updated_at">Last updated</option>
            <option value="created_at">Created</option>
            <option value="title">Title</option>
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : filtered.length === 0 ? (
        <p className="text-gray-500 text-sm">No projects yet. Use the actions above to get started.</p>
      ) : (
        <div className="grid gap-3">
          {filtered.map(p => (
            <div key={p.id} className="border rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50/30 transition-colors flex items-center justify-between">
              <button
                onClick={() => navigate(`/projects/${p.id}`)}
                className="flex-1 text-left"
              >
                <h3 className="font-medium text-gray-900">{p.title}</h3>
                {p.description && <p className="text-sm text-gray-500 mt-0.5">{p.description}</p>}
                <p className="text-xs text-gray-400 mt-2">
                  Updated {new Date(p.updated_at).toLocaleDateString()}
                </p>
              </button>
              <div className="flex items-center gap-3 ml-4">
                <span className="text-xs text-gray-400">{p.current_stage}</span>
                <StatusBadge status={p.status} />
                <button
                  onClick={() => handleDelete(p.id)}
                  className="text-gray-400 hover:text-red-500 text-sm"
                  aria-label={`Delete ${p.title}`}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-lg" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-4">New Project</h2>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="project-title">Title</label>
            <input
              id="project-title"
              value={title}
              onChange={e => setTitle(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm mb-3"
              placeholder="My Video Project"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
            />
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="project-desc">Description</label>
            <textarea
              id="project-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm mb-4"
              rows={3}
              placeholder="Optional description..."
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Cancel</button>
              <button onClick={handleCreate} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
