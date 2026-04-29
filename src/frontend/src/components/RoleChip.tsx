interface RoleChipProps {
  role: string
  count: number
}

function formatRole(role: string): string {
  return role
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export default function RoleChip({ role, count }: RoleChipProps) {
  if (count === 0) return null
  return (
    <span className="inline-block bg-gray-800 border border-gray-600 rounded px-2 py-1 text-xs">
      {formatRole(role)} ×{count}
    </span>
  )
}
