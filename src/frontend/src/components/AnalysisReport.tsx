import type { TeamAnalysisResponse } from '../api/types'
import TypeBadge from './TypeBadge'
import RoleChip from './RoleChip'

interface AnalysisReportProps {
  analysis: TeamAnalysisResponse
}

const ARCHETYPE_LABELS: Record<string, string> = {
  tailwind: 'Tailwind',
  trick_room: 'Trick Room',
  hybrid: 'Hybrid (TW + TR)',
  none: 'None',
}

export default function AnalysisReport({ analysis }: AnalysisReportProps) {
  const sortedWeaknesses = Object.entries(analysis.weaknesses)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)

  const sortedResistances = Object.entries(analysis.resistances)
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)

  return (
    <div className="space-y-4 text-sm">
      {/* Validity */}
      <div>
        {analysis.valid ? (
          <span className="text-green-400 font-medium">✓ Valid team</span>
        ) : (
          <div>
            <span className="text-red-400 font-medium">✗ Issues found</span>
            <ul className="mt-1 list-disc list-inside text-red-300 text-xs space-y-0.5">
              {analysis.issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Speed control archetype */}
      <div>
        <span className="text-gray-400 text-xs uppercase tracking-wide">Speed Control</span>
        <div className="mt-1">
          <span className="bg-blue-900 text-blue-300 border border-blue-700 rounded px-2 py-0.5 text-xs">
            {ARCHETYPE_LABELS[analysis.speed_control_archetype] ?? analysis.speed_control_archetype}
          </span>
        </div>
      </div>

      {/* Roles */}
      <div>
        <span className="text-gray-400 text-xs uppercase tracking-wide">Roles</span>
        <div className="mt-1 flex flex-wrap gap-1">
          {Object.entries(analysis.roles).map(([role, count]) => (
            <RoleChip key={role} role={role} count={count} />
          ))}
        </div>
      </div>

      {/* Weaknesses */}
      {sortedWeaknesses.length > 0 && (
        <div>
          <span className="text-gray-400 text-xs uppercase tracking-wide">Weaknesses</span>
          <div className="mt-1 flex flex-wrap gap-2">
            {sortedWeaknesses.map(([type, count]) => (
              <span key={type} className="flex items-center gap-1">
                <TypeBadge typeName={type} />
                <span className="text-xs text-gray-400">×{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Resistances */}
      {sortedResistances.length > 0 && (
        <div>
          <span className="text-gray-400 text-xs uppercase tracking-wide">Resistances</span>
          <div className="mt-1 flex flex-wrap gap-2">
            {sortedResistances.map(([type, count]) => (
              <span key={type} className="flex items-center gap-1">
                <TypeBadge typeName={type} />
                <span className="text-xs text-gray-400">×{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Coverage gaps */}
      {analysis.coverage.missing_types.length > 0 && (
        <div>
          <span className="text-gray-400 text-xs uppercase tracking-wide">Coverage Gaps</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {analysis.coverage.missing_types.map((type) => (
              <span key={type} className="opacity-60">
                <TypeBadge typeName={type} />
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
