import { useState, useEffect } from 'react'
import * as effectsApi from '@/api/effects'
import type { EffectSummary, EffectDetail } from '@/api/effects'

interface Props {
  onApply?: (identifier: string, defaults: Record<string, unknown>) => void
  onClose?: () => void
}

const CATEGORIES = ['all', 'charts', 'text', 'social', 'data', 'editorial', 'narrative', 'motion']

export function EffectBrowser({ onApply, onClose }: Props) {
  const [effects, setEffects] = useState<EffectSummary[]>([])
  const [selected, setSelected] = useState<EffectDetail | null>(null)
  const [category, setCategory] = useState('all')
  const [aliases, setAliases] = useState<Record<string, string>>({})
  const [quality, setQuality] = useState('production')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const [effs, als] = await Promise.all([
        effectsApi.listEffects(category === 'all' ? undefined : category),
        effectsApi.listAliases(),
      ])
      setEffects(effs)
      setAliases(als)
      setLoading(false)
    }
    load()
  }, [category])

  const selectEffect = async (id: string) => {
    const detail = await effectsApi.getEffect(id)
    setSelected(detail)
  }

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0 }}>Effect Browser</h3>
        {onClose && <button onClick={onClose}>Close</button>}
      </div>

      {/* Category filter */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => { setCategory(cat); setSelected(null) }}
            style={{
              padding: '0.25rem 0.75rem',
              borderRadius: '4px',
              border: '1px solid #333',
              background: category === cat ? '#5AC8FA' : '#1a1a1a',
              color: category === cat ? '#000' : '#e6edf3',
              cursor: 'pointer',
            }}
          >
            {cat}
          </button>
        ))}
      </div>

      {loading ? (
        <p>Loading effects...</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
          {effects.map(eff => (
            <button
              key={eff.identifier}
              onClick={() => selectEffect(eff.identifier)}
              style={{
                padding: '0.75rem',
                borderRadius: '8px',
                border: selected?.identifier === eff.identifier ? '2px solid #5AC8FA' : '1px solid #333',
                background: '#1a1a1a',
                color: '#e6edf3',
                textAlign: 'left',
                cursor: 'pointer',
              }}
            >
              <strong>{eff.display_name}</strong>
              <div style={{ fontSize: '0.75rem', color: '#888', marginTop: '0.25rem' }}>{eff.category}</div>
              <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>{eff.description}</div>
            </button>
          ))}
        </div>
      )}

      {/* Detail panel */}
      {selected && (
        <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #333', borderRadius: '8px', background: '#111' }}>
          <h4 style={{ margin: '0 0 0.5rem' }}>{selected.display_name}</h4>
          <p style={{ color: '#aaa', margin: '0 0 0.5rem' }}>{selected.description}</p>

          {selected.sync_points.length > 0 && (
            <div style={{ marginBottom: '0.5rem' }}>
              <strong style={{ fontSize: '0.8rem' }}>Sync Points:</strong>{' '}
              <span style={{ fontSize: '0.8rem', color: '#5AC8FA' }}>{selected.sync_points.join(', ')}</span>
            </div>
          )}

          {/* Quality profile selector */}
          <div style={{ marginBottom: '0.75rem' }}>
            <label htmlFor="quality-select" style={{ fontSize: '0.8rem', marginRight: '0.5rem' }}>Quality:</label>
            <select
              id="quality-select"
              value={quality}
              onChange={e => setQuality(e.target.value)}
              style={{ background: '#1a1a1a', color: '#e6edf3', border: '1px solid #333', borderRadius: '4px', padding: '0.25rem' }}
            >
              {Object.keys(selected.quality_profiles).map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          {/* Parameter schema preview */}
          {Object.keys(selected.parameter_schema).length > 0 && (
            <details style={{ marginBottom: '0.75rem' }}>
              <summary style={{ cursor: 'pointer', fontSize: '0.8rem' }}>Parameter Schema</summary>
              <pre style={{ fontSize: '0.7rem', overflow: 'auto', maxHeight: '200px', background: '#0a0a0a', padding: '0.5rem', borderRadius: '4px' }}>
                {JSON.stringify(selected.parameter_schema, null, 2)}
              </pre>
            </details>
          )}

          {onApply && (
            <button
              onClick={() => onApply(selected.identifier, selected.preview_config)}
              style={{
                padding: '0.5rem 1rem',
                background: '#5AC8FA',
                color: '#000',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
              }}
            >
              Apply to Scene
            </button>
          )}
        </div>
      )}

      {/* Legacy aliases */}
      {Object.keys(aliases).length > 0 && (
        <details style={{ marginTop: '1rem' }}>
          <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: '#888' }}>Legacy Aliases</summary>
          <div style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
            {Object.entries(aliases).map(([from, to]) => (
              <div key={from}><code>{from}</code> → <code>{to}</code></div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
