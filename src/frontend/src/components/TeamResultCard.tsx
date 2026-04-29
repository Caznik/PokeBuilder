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
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-4">
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
          <div key={i} className="bg-gray-800 rounded px-3 py-1.5 text-center">
            <div className="text-sm font-medium">{titleCase(m.pokemon_name)}</div>
            <div className="text-xs text-gray-500">
              {m.set_name
                ? m.set_name
                : [m.nature, m.ability].filter(Boolean).map(titleCase).join(' · ') || null}
            </div>
          </div>
        ))}
      </div>

      {/* Breakdown collapsible */}
      <details className="group">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-200 select-none">
          ▶ Score Breakdown
        </summary>
        <div className="mt-3 pl-2">
          <BreakdownTable breakdown={team.breakdown} />
        </div>
      </details>

      {/* Analysis collapsible */}
      <details className="group">
        <summary className="cursor-pointer text-xs text-gray-400 hover:text-gray-200 select-none">
          ▶ Team Analysis
        </summary>
        <div className="mt-3 pl-2">
          <AnalysisReport analysis={team.analysis} />
        </div>
      </details>
    </div>
  )
}
