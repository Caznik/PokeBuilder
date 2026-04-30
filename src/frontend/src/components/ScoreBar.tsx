interface ScoreBarProps {
  score: number
  maxScore?: number
}

export default function ScoreBar({ score, maxScore = 10 }: ScoreBarProps) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100))
  const ratio = score / maxScore
  const barColor =
    ratio >= 0.7
      ? 'oklch(0.85 0.18 130)'
      : ratio >= 0.4
        ? 'oklch(0.75 0.15 80)'
        : 'oklch(0.55 0.18 25)'

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 rounded overflow-hidden"
        style={{ height: 6, background: 'oklch(0.22 0.005 250)' }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: barColor,
            borderRadius: 3,
            transition: 'width 0.25s',
          }}
        />
      </div>
      <span
        className="text-right w-8"
        style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'oklch(0.92 0.005 250)', fontVariantNumeric: 'tabular-nums' }}
      >
        {maxScore === 10 ? score.toFixed(1) : score.toFixed(2)}
      </span>
    </div>
  )
}
