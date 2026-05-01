import { useState } from 'react'
import type { TeamResult } from '../api/types'
import ScoreBar from './ScoreBar'
import BreakdownTable from './BreakdownTable'
import AnalysisReport from './AnalysisReport'

interface TeamResultCardProps {
  team: TeamResult
  rank: number
  onSave?: (name: string) => Promise<void>
}

function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

export default function TeamResultCard({ team, rank, onSave }: TeamResultCardProps) {
  const [saving, setSaving] = useState(false)
  const [saveInput, setSaveInput] = useState('')
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  async function handleSaveConfirm() {
    if (!saveInput.trim()) return
    setSaving(true)
    setSaveError(null)
    try {
      await onSave!(saveInput.trim())
      setSaved(true)
      setShowSaveInput(false)
      setSaveInput('')
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded-lg p-4 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      {/* Header */}
      <div className="flex items-center gap-4">
        <span className="text-gray-400 font-medium">Team #{rank}</span>
        <div className="flex-1">
          <ScoreBar score={team.score} maxScore={10} />
        </div>
        {onSave && !saved && (
          <button
            onClick={() => setShowSaveInput((v) => !v)}
            style={{
              fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
              letterSpacing: '0.06em', color: 'var(--accent)', background: 'none',
              border: '1px solid var(--accent)', borderRadius: 4, padding: '2px 8px', cursor: 'pointer',
            }}
          >
            Save
          </button>
        )}
        {saved && (
          <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
            Saved ✓
          </span>
        )}
      </div>

      {/* Inline save input */}
      {showSaveInput && onSave && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={saveInput}
            onChange={(e) => setSaveInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSaveConfirm()}
            placeholder="Team name..."
            autoFocus
            style={{
              flex: 1, background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
              color: 'var(--text)', borderRadius: 4, padding: '4px 8px', fontSize: 12,
              fontFamily: 'var(--font-mono)',
            }}
          />
          <button
            onClick={handleSaveConfirm}
            disabled={saving || !saveInput.trim()}
            style={{
              fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
              letterSpacing: '0.06em', background: 'var(--accent)', color: 'var(--accent-fg)',
              border: 'none', borderRadius: 4, padding: '4px 10px', cursor: 'pointer',
              opacity: saving || !saveInput.trim() ? 0.4 : 1,
            }}
          >
            {saving ? '...' : 'Confirm'}
          </button>
          <button
            onClick={() => { setShowSaveInput(false); setSaveInput(''); setSaveError(null) }}
            style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      )}
      {saveError && <p style={{ fontSize: 11, color: 'oklch(0.55 0.18 25)', margin: 0 }}>{saveError}</p>}

      {/* Members */}
      <div className="flex flex-wrap gap-2">
        {team.members.map((m, i) => (
          <div key={i} className="rounded px-3 py-1.5 text-center" style={{ background: 'var(--surface-2)' }}>
            <div className="text-sm font-medium" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{titleCase(m.pokemon_name)}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {m.set_name
                ? m.set_name
                : [m.nature, m.ability].filter((x): x is string => x !== null && x !== undefined).map(titleCase).join(' · ') || null}
            </div>
          </div>
        ))}
      </div>

      {/* Breakdown collapsible */}
      <details className="group">
        <summary className="cursor-pointer select-none" style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
          ▶ Score Breakdown
        </summary>
        <div className="mt-3 pl-2">
          <BreakdownTable breakdown={team.breakdown} />
        </div>
      </details>

      {/* Analysis collapsible */}
      <details className="group">
        <summary className="cursor-pointer select-none" style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
          ▶ Team Analysis
        </summary>
        <div className="mt-3 pl-2">
          <AnalysisReport analysis={team.analysis} />
        </div>
      </details>
    </div>
  )
}
