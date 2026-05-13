import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { BattleLogOut } from '../api/types'
import StatCard from '../components/StatCard'
import WinRateTrend, { type TrendPoint } from '../components/WinRateTrend'

const TREND_WINDOW = 10

function computeStreak(logs: BattleLogOut[]): string {
  if (logs.length === 0) return '—'
  const sorted = [...logs].sort(
    (a, b) => new Date(b.played_at).getTime() - new Date(a.played_at).getTime(),
  )
  const first = sorted[0].result
  let count = 0
  for (const log of sorted) {
    if (log.result !== first) break
    count++
  }
  const prefix = first === 'win' ? 'W' : first === 'loss' ? 'L' : 'T'
  return `${prefix}${count}`
}

function computeTrend(logs: BattleLogOut[]): TrendPoint[] {
  const sorted = [...logs].sort(
    (a, b) => new Date(a.played_at).getTime() - new Date(b.played_at).getTime(),
  )
  const points: TrendPoint[] = []
  for (let i = 0; i + TREND_WINDOW <= sorted.length; i += TREND_WINDOW) {
    const window = sorted.slice(i, i + TREND_WINDOW)
    const wins = window.filter((l) => l.result === 'win').length
    points.push({
      label: `${i + 1}–${i + TREND_WINDOW}`,
      winRate: Math.round((wins / TREND_WINDOW) * 100),
    })
  }
  return points
}

function Skeleton() {
  return (
    <div
      data-testid="skeleton"
      className="h-24 rounded-lg animate-pulse"
      style={{ background: 'var(--surface-2)' }}
    />
  )
}

export default function Dashboard() {
  const [logs, setLogs] = useState<BattleLogOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function fetchStats() {
    setLoading(true)
    setError(null)
    api.battleLogs
      .list()
      .then(setLogs)
      .catch(() => setError('Failed to load battle stats.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const stats = useMemo(() => {
    const total = logs.length
    const wins = logs.filter((l) => l.result === 'win').length
    const losses = logs.filter((l) => l.result === 'loss').length
    const ties = logs.filter((l) => l.result === 'tie').length
    const winRate = total === 0 ? 0 : Math.round((wins / total) * 100)
    const vgcCount = logs.filter((l) => l.format === 'vgc').length
    const singlesCount = logs.filter((l) => l.format === 'singles').length
    const vgcPct = total === 0 ? 0 : Math.round((vgcCount / total) * 100)
    const singlesPct = total === 0 ? 0 : Math.round((singlesCount / total) * 100)
    const formatSplit =
      total === 0 ? '—' : `VGC ${vgcPct}% / Singles ${singlesPct}%`
    const streak = computeStreak(logs)
    const trendData = computeTrend(logs)
    return { total, wins, losses, ties, winRate, formatSplit, streak, trendData }
  }, [logs])

  if (loading) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton />
          <Skeleton />
        </div>
        <Skeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="rounded-lg p-6 text-center"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <p className="mb-3" style={{ color: 'var(--text-muted)' }}>
          {error}
        </p>
        <button
          onClick={fetchStats}
          className="text-sm px-4 py-1.5 rounded"
          style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
        >
          Retry
        </button>
      </div>
    )
  }

  if (stats.total === 0) {
    return (
      <div
        className="rounded-lg p-8 text-center"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <p className="text-lg font-semibold mb-2" style={{ color: 'var(--text)' }}>
          No battles yet
        </p>
        <p className="mb-4" style={{ color: 'var(--text-muted)' }}>
          Log your first battle to see your stats here.
        </p>
        <Link
          to="/battle-results"
          className="text-sm px-4 py-1.5 rounded"
          style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
        >
          Go to Battle Results
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Hero card */}
      <div
        className="rounded-lg p-6"
        style={{ background: 'var(--surface)', border: '1px solid var(--accent)' }}
      >
        <p className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
          Win Rate
        </p>
        <p className="text-5xl font-bold mb-2" style={{ color: 'var(--accent)' }}>
          {stats.winRate}%
        </p>
        <div className="flex items-center gap-3 text-sm font-medium">
          <span style={{ color: 'var(--color-win)' }}>{stats.wins}W</span>
          <span style={{ color: 'var(--text-dim)' }}>·</span>
          <span style={{ color: 'var(--color-loss)' }}>{stats.losses}L</span>
          <span style={{ color: 'var(--text-dim)' }}>·</span>
          <span style={{ color: 'var(--color-tie)' }}>{stats.ties}T</span>
          <span style={{ color: 'var(--text-dim)' }}>·</span>
          <span style={{ color: 'var(--text-muted)' }}>{stats.total} battles</span>
        </div>
      </div>

      {/* Supporting cards */}
      <div className="grid grid-cols-2 gap-4">
        <StatCard label="Format Split" value={stats.formatSplit} />
        <StatCard label="Current Streak" value={stats.streak} />
      </div>

      {/* Trend chart or threshold note */}
      {stats.trendData.length > 0 ? (
        <WinRateTrend data={stats.trendData} />
      ) : (
        <div
          className="rounded-lg p-4 text-center text-sm"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
          }}
        >
          Play at least 10 battles to see your win rate trend.
        </div>
      )}
    </div>
  )
}
