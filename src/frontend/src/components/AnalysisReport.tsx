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

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 9,
        fontFamily: 'var(--font-mono)',
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
        color: 'var(--text-dim)',
        marginBottom: 6,
      }}
    >
      {children}
    </div>
  )
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
          <span style={{ color: 'var(--accent)', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600 }}>
            ✓ Valid team
          </span>
        ) : (
          <div>
            <span style={{ color: 'oklch(0.65 0.18 25)', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600 }}>
              ✗ Issues found
            </span>
            <ul className="mt-1 list-disc list-inside space-y-0.5" style={{ fontSize: 11, color: 'oklch(0.60 0.14 25)' }}>
              {analysis.issues.map((issue, i) => (
                <li key={i}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Speed control archetype */}
      <div>
        <SectionLabel>Speed Control</SectionLabel>
        <span
          style={{
            background: 'oklch(0.22 0.04 130)',
            color: 'var(--accent)',
            border: '1px solid oklch(0.35 0.08 130)',
            borderRadius: 4,
            padding: '2px 8px',
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            fontWeight: 500,
            display: 'inline-block',
          }}
        >
          {ARCHETYPE_LABELS[analysis.speed_control_archetype] ?? analysis.speed_control_archetype}
        </span>
      </div>

      {/* Roles */}
      <div>
        <SectionLabel>Roles</SectionLabel>
        <div className="flex flex-wrap gap-1">
          {Object.entries(analysis.roles).map(([role, count]) => (
            <RoleChip key={role} role={role} count={count} />
          ))}
        </div>
      </div>

      {/* Weaknesses */}
      {sortedWeaknesses.length > 0 && (
        <div>
          <SectionLabel>Weaknesses</SectionLabel>
          <div className="flex flex-wrap gap-2">
            {sortedWeaknesses.map(([type, count]) => (
              <span key={type} className="flex items-center gap-1">
                <TypeBadge typeName={type} />
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>×{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Resistances */}
      {sortedResistances.length > 0 && (
        <div>
          <SectionLabel>Resistances</SectionLabel>
          <div className="flex flex-wrap gap-2">
            {sortedResistances.map(([type, count]) => (
              <span key={type} className="flex items-center gap-1">
                <TypeBadge typeName={type} />
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>×{count}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Coverage gaps */}
      {analysis.coverage.missing_types.length > 0 && (
        <div>
          <SectionLabel>Coverage Gaps</SectionLabel>
          <div className="flex flex-wrap gap-1">
            {analysis.coverage.missing_types.map((type) => (
              <span key={type} style={{ opacity: 0.55 }}>
                <TypeBadge typeName={type} />
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
