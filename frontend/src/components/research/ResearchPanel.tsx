import { useState, useEffect, useCallback } from 'react'
import * as researchApi from '@/api/research'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { WebSocketMessage } from '@/types'

type SourceKey = 'youtube' | 'reddit' | 'trends' | 'finance' | 'wikipedia'

interface ResearchItem {
  title: string
  source: string
  score: number
  category?: string
  keywords?: string[]
  meta: Record<string, unknown>
}

const sources: { key: SourceKey; label: string; trigger: (id: string) => Promise<unknown> }[] = [
  { key: 'youtube', label: 'YouTube', trigger: researchApi.searchYouTube },
  { key: 'reddit', label: 'Reddit', trigger: researchApi.searchReddit },
  { key: 'trends', label: 'Google Trends', trigger: researchApi.searchTrends },
  { key: 'finance', label: 'Yahoo Finance', trigger: researchApi.searchFinance },
  { key: 'wikipedia', label: 'Wikipedia', trigger: researchApi.searchWikipedia },
]

function parseResults(jobs: Array<Record<string, unknown>>): ResearchItem[] {
  const items: ResearchItem[] = []

  for (const job of jobs) {
    if (job.status !== 'COMPLETED' || !job.output) continue
    const output = job.output as Record<string, unknown>
    const jobType = job.job_type as string

    // YouTube results
    if (jobType === 'research_youtube') {
      const topics = (output.topics as Array<Record<string, unknown>>) || []
      for (const t of topics) {
        items.push({
          title: (t.topic_name as string) || 'Untitled',
          source: 'youtube',
          score: (t.trend_score as number) || 0,
          category: t.category as string,
          keywords: [],
          meta: t,
        })
      }
    }

    // Reddit results
    if (jobType === 'research_reddit') {
      const posts = (output.posts as Array<Record<string, unknown>>) || []
      for (const p of posts) {
        items.push({
          title: (p.title as string) || 'Untitled',
          source: 'reddit',
          score: (p.score as number) || 0,
          category: `r/${(p.subreddit as string) || '?'} · ${(p.comment_count as number) || 0} comments`,
          meta: p,
        })
      }
    }

    // Google Trends results
    if (jobType === 'research_trends') {
      const trends = (output.trends as Array<Record<string, unknown>>) || []
      for (const t of trends) {
        const relatedQueries = (t.related_queries as string[]) || []
        items.push({
          title: (t.topic_name as string) || 'Untitled',
          source: 'trends',
          score: (t.approximate_search_volume as number) || 0,
          keywords: relatedQueries.slice(0, 3),
          meta: t,
        })
      }
    }

    // Yahoo Finance results — combine gainers, losers, most_active, story_triggers
    if (jobType === 'research_finance') {
      const sections: [string, Array<Record<string, unknown>>][] = [
        ['gainer', (output.gainers as Array<Record<string, unknown>>) || []],
        ['loser', (output.losers as Array<Record<string, unknown>>) || []],
        ['active', (output.most_active as Array<Record<string, unknown>>) || []],
      ]
      const seen = new Set<string>()
      for (const [tag, movers] of sections) {
        for (const m of movers) {
          const sym = m.symbol as string
          if (seen.has(sym)) continue
          seen.add(sym)
          const pct = (m.change_percent as number) || 0
          items.push({
            title: `${(m.name as string) || sym} (${sym})`,
            source: 'finance',
            score: Math.abs(pct),
            category: `${tag} · ${pct >= 0 ? '+' : ''}${pct.toFixed(1)}% · $${((m.price as number) || 0).toFixed(2)}`,
            meta: m,
          })
        }
      }
    }

    // Wikipedia results
    if (jobType === 'research_wikipedia') {
      const events = (output.events as Array<Record<string, unknown>>) || []
      for (const e of events) {
        const headline = (e.headline as string) || (e.title as string) || (e.text as string) || 'Untitled'
        items.push({
          title: headline,
          source: 'wikipedia',
          score: 0,
          category: (e.category as string) || (e.date as string) || '',
          meta: e,
        })
      }
    }

    // Cross-reference unified results
    if (jobType === 'cross_reference') {
      const unified = (output.unified as Array<Record<string, unknown>>) || []
      for (const u of unified) {
        items.push({
          title: (u.topic_name as string) || (u.title as string) || 'Untitled',
          source: ((u.sources as string[]) || []).join(', ') || 'cross-ref',
          score: (u.trend_score as number) || 0,
          category: u.category as string,
          keywords: (u.keywords as string[]) || [],
          meta: u,
        })
      }
    }
  }

  // Normalize all scores to 0-100 scale per source
  const bySource = new Map<string, ResearchItem[]>()
  for (const item of items) {
    const key = item.source
    if (!bySource.has(key)) bySource.set(key, [])
    bySource.get(key)!.push(item)
  }

  for (const [source, group] of bySource) {
    // YouTube trend_score and cross-ref are already 0-100
    if (source === 'youtube' || source.includes(',')) continue

    if (source === 'wikipedia') {
      // Wikipedia has no numeric score — assign 50 as baseline
      for (const item of group) item.score = 50
      continue
    }

    // For reddit, trends, finance: normalize relative to max in group
    const maxScore = Math.max(...group.map(i => i.score), 1)
    for (const item of group) {
      item.score = (item.score / maxScore) * 100
    }
  }

  // Sort by score descending
  items.sort((a, b) => b.score - a.score)
  return items
}

interface Props {
  projectId: string
  lastMessage: WebSocketMessage | null
}

export function ResearchPanel({ projectId, lastMessage }: Props) {
  const [sourceStatus, setSourceStatus] = useState<Record<string, string>>({})
  const [items, setItems] = useState<ResearchItem[]>([])
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadResults = useCallback(async () => {
    try {
      const r = await researchApi.getResults(projectId) as Array<Record<string, unknown>>
      setItems(parseResults(r))

      // Update source statuses from jobs
      const statuses: Record<string, string> = {}
      for (const j of r) {
        const type = (j.job_type as string).replace('research_', '')
        statuses[type] = (j.status as string)
      }
      setSourceStatus(statuses)
    } catch { /* no results yet */ }
  }, [projectId])

  useEffect(() => { loadResults() }, [loadResults])

  // React to WebSocket job events
  useEffect(() => {
    if (!lastMessage) return
    const { event, job_type } = lastMessage
    if (job_type?.startsWith('research_') || job_type === 'cross_reference') {
      const src = job_type.replace('research_', '')
      if (event === 'job_completed') {
        setSourceStatus(prev => ({ ...prev, [src]: 'COMPLETED' }))
        loadResults()
      } else if (event === 'job_failed') {
        setSourceStatus(prev => ({ ...prev, [src]: 'FAILED' }))
        loadResults()
      } else if (event === 'job_started') {
        setSourceStatus(prev => ({ ...prev, [src]: 'RUNNING' }))
      }
    }
  }, [lastMessage, loadResults])

  const triggerSource = async (key: SourceKey, fn: (id: string) => Promise<unknown>) => {
    setSourceStatus(prev => ({ ...prev, [key]: 'RUNNING' }))
    setError(null)
    try {
      await fn(projectId)
      // Poll for completion since these are synchronous calls that return results
      await loadResults()
    } catch (e) {
      setSourceStatus(prev => ({ ...prev, [key]: 'FAILED' }))
      setError(e instanceof Error ? e.message : 'Research failed')
    }
  }

  const triggerCrossRef = async () => {
    setLoading(true)
    setError(null)
    setSourceStatus(prev => ({ ...prev, cross_reference: 'RUNNING' }))
    try {
      await researchApi.crossReference(projectId)
      await loadResults()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Cross-reference failed')
      setSourceStatus(prev => ({ ...prev, cross_reference: 'FAILED' }))
    } finally { setLoading(false) }
  }

  // Filter items
  const filtered = items.filter(item => {
    if (sourceFilter !== 'all' && !item.source.includes(sourceFilter)) return false
    if (search) {
      const q = search.toLowerCase()
      return item.title.toLowerCase().includes(q)
        || (item.category?.toLowerCase().includes(q) ?? false)
        || (item.keywords?.some(k => k.toLowerCase().includes(q)) ?? false)
    }
    return true
  })

  const activeSources = [...new Set(items.map(i => i.source))]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-medium mb-3">Data Sources</h2>
        <div className="flex flex-wrap gap-2 mb-3">
          {sources.map(s => {
            const status = sourceStatus[s.key]
            const isRunning = status === 'RUNNING'
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => triggerSource(s.key, s.trigger)}
                disabled={isRunning}
                className="px-4 py-2 border rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50 flex items-center gap-2 transition-colors"
              >
                {isRunning && <span className="animate-spin text-xs">⏳</span>}
                {s.label}
                {status && <StatusBadge status={status} />}
              </button>
            )
          })}
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={triggerCrossRef}
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <span className="animate-spin text-xs">⏳</span>}
            {loading ? 'Cross-referencing...' : 'Cross-Reference All'}
            {sourceStatus.cross_reference && <StatusBadge status={sourceStatus.cross_reference} />}
          </button>
        </div>
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
      </div>

      {/* Results */}
      {items.length > 0 && (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-lg font-medium">Results ({filtered.length})</h2>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm flex-1 max-w-xs"
              placeholder="Search results..."
              aria-label="Search research results"
            />
            <select
              value={sourceFilter}
              onChange={e => setSourceFilter(e.target.value)}
              className="border rounded-lg px-3 py-1.5 text-sm"
              aria-label="Filter by source"
            >
              <option value="all">All sources</option>
              {activeSources.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="grid gap-2 max-h-[60vh] overflow-y-auto">
            {filtered.map((item, idx) => (
              <div key={idx} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 text-sm">{item.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">{item.source}</span>
                      {item.category && <span className="text-xs text-gray-400">{item.category}</span>}
                      {item.keywords && item.keywords.length > 0 && (
                        <div className="flex gap-1">
                          {item.keywords.slice(0, 3).map((kw, i) => (
                            <span key={i} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{kw}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right ml-3 w-16">
                    <span className="text-sm font-mono font-medium text-gray-700">
                      {Math.round(item.score)}
                    </span>
                    <div className="w-full bg-gray-100 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full"
                        style={{ width: `${Math.min(item.score, 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
