const TYPE_COLORS: Record<string, { bg: string; fg: string }> = {
  normal:   { bg: 'oklch(0.55 0.02 80)',  fg: 'oklch(0.92 0.01 80)' },
  fire:     { bg: 'oklch(0.55 0.16 35)',  fg: 'oklch(0.95 0.05 35)' },
  water:    { bg: 'oklch(0.55 0.13 240)', fg: 'oklch(0.95 0.04 240)' },
  electric: { bg: 'oklch(0.65 0.16 95)',  fg: 'oklch(0.20 0.05 95)' },
  grass:    { bg: 'oklch(0.55 0.13 145)', fg: 'oklch(0.95 0.04 145)' },
  ice:      { bg: 'oklch(0.70 0.10 200)', fg: 'oklch(0.20 0.05 200)' },
  fighting: { bg: 'oklch(0.50 0.15 25)',  fg: 'oklch(0.95 0.04 25)' },
  poison:   { bg: 'oklch(0.50 0.14 320)', fg: 'oklch(0.95 0.04 320)' },
  ground:   { bg: 'oklch(0.55 0.10 65)',  fg: 'oklch(0.95 0.04 65)' },
  flying:   { bg: 'oklch(0.65 0.08 260)', fg: 'oklch(0.20 0.04 260)' },
  psychic:  { bg: 'oklch(0.60 0.14 350)', fg: 'oklch(0.95 0.04 350)' },
  bug:      { bg: 'oklch(0.60 0.13 120)', fg: 'oklch(0.95 0.04 120)' },
  rock:     { bg: 'oklch(0.50 0.07 70)',  fg: 'oklch(0.95 0.03 70)' },
  ghost:    { bg: 'oklch(0.45 0.10 290)', fg: 'oklch(0.95 0.04 290)' },
  dragon:   { bg: 'oklch(0.50 0.16 270)', fg: 'oklch(0.95 0.05 270)' },
  dark:     { bg: 'oklch(0.35 0.04 30)',  fg: 'oklch(0.92 0.02 30)' },
  steel:    { bg: 'oklch(0.60 0.03 230)', fg: 'oklch(0.20 0.01 230)' },
  fairy:    { bg: 'oklch(0.75 0.10 350)', fg: 'oklch(0.20 0.04 350)' },
}

const FALLBACK = { bg: 'oklch(0.30 0.005 250)', fg: 'oklch(0.75 0.01 250)' }

interface TypeBadgeProps {
  typeName: string
}

export default function TypeBadge({ typeName }: TypeBadgeProps) {
  const c = TYPE_COLORS[typeName.toLowerCase()] ?? FALLBACK
  return (
    <span
      style={{
        background: c.bg,
        color: c.fg,
        padding: '2px 8px',
        borderRadius: 999,
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        fontFamily: 'var(--font-mono)',
        display: 'inline-block',
        lineHeight: 1.5,
      }}
    >
      {typeName}
    </span>
  )
}
