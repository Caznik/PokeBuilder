import type { TeamResult } from '../api/types'
import ScoreBar from './ScoreBar'
import BreakdownTable from './BreakdownTable'
import AnalysisReport from './AnalysisReport'

interface TeamResultCardProps {
  team: TeamResult
  rank: number
}

function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

export default function TeamResultCard({ team, rank }: TeamResultCardProps) {
  return (
    <div className="rounded-lg p-4 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      {/* Header */}
      <div className="flex items-center gap-4">
        <span className="text-gray-400 font-medium">Team #{rank}</span>
        <div className="flex-1">
          <ScoreBar score={team.score} maxScore={10} />
        </div>
      </div>

      {/* Members */}
      <div className="flex flex-wrap gap-2">
        {team.members.map((m, i) => (
          <div key={i} className="rounded px-3 py-1.5 text-center" style={{ background: 'var(--surface-2)' }}>
            <div className="text-sm font-medium" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{titleCase(m.pokemon_name)}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {m.set_name
                ? m.set_name
                : [m.nature, m.ability].filter(Boolean).map(titleCase).join(' · ') || null}
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
