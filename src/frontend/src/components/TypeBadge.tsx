// Official Pokédex identity colors — fixed values, intentionally not theme tokens.
const TYPE_COLORS: Record<string, { bg: string; fg: string }> = {
  normal:   { bg: '#A8A77A', fg: '#fff' },
  fire:     { bg: '#EE8130', fg: '#fff' },
  water:    { bg: '#6390F0', fg: '#fff' },
  electric: { bg: '#F7D02C', fg: '#333' },
  grass:    { bg: '#7AC74C', fg: '#fff' },
  ice:      { bg: '#96D9D6', fg: '#333' },
  fighting: { bg: '#C22E28', fg: '#fff' },
  poison:   { bg: '#A33EA1', fg: '#fff' },
  ground:   { bg: '#E2BF65', fg: '#333' },
  flying:   { bg: '#A98FF3', fg: '#fff' },
  psychic:  { bg: '#F95587', fg: '#fff' },
  bug:      { bg: '#A6B91A', fg: '#fff' },
  rock:     { bg: '#B6A136', fg: '#fff' },
  ghost:    { bg: '#735797', fg: '#fff' },
  dragon:   { bg: '#6F35FC', fg: '#fff' },
  dark:     { bg: '#705746', fg: '#fff' },
  steel:    { bg: '#B7B7CE', fg: '#333' },
  fairy:    { bg: '#D685AD', fg: '#fff' },
}

const FALLBACK = { bg: '#68A090', fg: '#222' }

interface TypeBadgeProps {
  typeName: string
  small?: boolean
}

export default function TypeBadge({ typeName, small }: TypeBadgeProps) {
  const c = TYPE_COLORS[typeName.toLowerCase()] ?? FALLBACK
  return (
    <span
      style={{
        background: c.bg,
        color: c.fg,
        padding: small ? '1px 6px' : '3px 10px',
        borderRadius: 999,
        fontSize: small ? 8 : 10,
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        fontFamily: 'Inter, sans-serif',
        display: 'inline-block',
        lineHeight: 1.5,
      }}
    >
      {typeName}
    </span>
  )
}
