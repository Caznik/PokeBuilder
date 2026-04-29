interface ScoreBarProps {
  score: number
  maxScore?: number
}

export default function ScoreBar({ score, maxScore = 10 }: ScoreBarProps) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100))
  const color =
    score / maxScore >= 0.7
      ? 'bg-green-500'
      : score / maxScore >= 0.4
        ? 'bg-yellow-500'
        : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-700 rounded h-2 overflow-hidden">
        <div className={`h-full rounded ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-300 w-8 text-right">
        {maxScore === 10 ? score.toFixed(1) : score.toFixed(2)}
      </span>
    </div>
  )
}
