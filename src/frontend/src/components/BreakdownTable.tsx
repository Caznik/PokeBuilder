import type { ScoreBreakdown } from '../api/types'
import ScoreBar from './ScoreBar'

interface BreakdownTableProps {
  breakdown: ScoreBreakdown
}

const LABELS: Record<keyof ScoreBreakdown, string> = {
  coverage: 'Coverage',
  defensive: 'Defensive',
  role: 'Role',
  speed_control: 'Speed Control',
  lead_pair: 'Lead Pair',
}

export default function BreakdownTable({ breakdown }: BreakdownTableProps) {
  return (
    <div className="space-y-2">
      {(Object.keys(LABELS) as (keyof ScoreBreakdown)[]).map((key) => (
        <div key={key} className="grid grid-cols-[120px_1fr_auto] items-center gap-3">
          <span className="text-xs text-gray-400">{LABELS[key]}</span>
          <ScoreBar score={breakdown[key].score} maxScore={1} />
          <span className="text-xs text-gray-500 text-right max-w-xs truncate" title={breakdown[key].reason}>
            {breakdown[key].reason}
          </span>
        </div>
      ))}
    </div>
  )
}
