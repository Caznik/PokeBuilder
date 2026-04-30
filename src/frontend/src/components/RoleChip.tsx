interface RoleChipProps {
  role: string
  count: number
}

function formatRole(role: string): string {
  return role.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

export default function RoleChip({ role, count }: RoleChipProps) {
  if (count === 0) return null
  return (
    <span
      style={{
        background: 'var(--surface-2)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 4,
        padding: '2px 8px',
        fontSize: 10,
        fontFamily: 'var(--font-mono)',
        color: 'oklch(0.75 0.01 250)',
        display: 'inline-block',
        lineHeight: 1.6,
      }}
    >
      {formatRole(role)} ×{count}
    </span>
  )
}
