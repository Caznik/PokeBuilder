interface StatCardProps {
  label: string
  value: string
  sublabel?: string
  accent?: boolean
}

export default function StatCard({ label, value, sublabel, accent = false }: StatCardProps) {
  return (
    <div
      className="rounded-lg p-4 flex flex-col gap-1"
      style={{
        background: 'var(--surface)',
        border: `1px solid ${accent ? 'var(--accent)' : 'var(--border)'}`,
      }}
    >
      <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span
        className="text-2xl font-bold"
        style={{ color: accent ? 'var(--accent)' : 'var(--text)' }}
      >
        {value}
      </span>
      {sublabel && (
        <span className="text-xs" style={{ color: 'var(--text-dim)' }}>
          {sublabel}
        </span>
      )}
    </div>
  )
}
