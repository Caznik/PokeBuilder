import type { ScoreBreakdown } from '../api/types'
import ScoreBar from './ScoreBar'

interface BreakdownTableProps {
  breakdown: ScoreBreakdown
}

const LABELS: Record<keyof ScoreBreakdown, string> = {
  coverage: 'Coverage',
  defensive: 'Defensive',
  role: 'Role',
  speed_control: 'Speed Ctrl',
  lead_pair: 'Lead Pair',
}

export default function BreakdownTable({ breakdown }: BreakdownTableProps) {
  return (
    <div className="space-y-2">
      {(Object.keys(LABELS) as (keyof ScoreBreakdown)[]).map((key) => (
        <div key={key} className="grid items-center gap-3" style={{ gridTemplateColumns: '80px 1fr auto' }}>
          <span
            style={{
              fontSize: 10,
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-dim)',
            }}
          >
            {LABELS[key]}
          </span>
          <ScoreBar score={breakdown[key].score} maxScore={1} />
          <span
            className="text-right max-w-xs truncate"
            style={{ fontSize: 10, color: 'var(--text-muted)' }}
            title={breakdown[key].reason}
          >
            {breakdown[key].reason}
          </span>
        </div>
      ))}
    </div>
  )
}
