import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, cleanup } from '@testing-library/react'
import { renderWithRouter } from '../test-utils'
import Dashboard from '../../pages/Dashboard'
import { api } from '../../api/client'
import type { BattleLogOut } from '../../api/types'

vi.mock('../../api/client', () => ({
  api: {
    battleLogs: { list: vi.fn() },
  },
}))

// Recharts uses ResizeObserver which is absent in jsdom
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  CartesianGrid: () => null,
}))

let _idCounter = 0

function _makeLog(
  result: 'win' | 'loss' | 'tie',
  format: 'singles' | 'vgc',
  offsetDays = 0,
): BattleLogOut {
  const d = new Date('2026-01-01T00:00:00Z')
  d.setDate(d.getDate() + offsetDays)
  return {
    id: ++_idCounter,
    user_id: 1,
    saved_team_id: null,
    saved_team_name: null,
    regulation_id: null,
    format,
    brought_pokemon: [],
    enemy_team: [],
    enemy_brought: [],
    result,
    notes: null,
    played_at: d.toISOString(),
    saved_team_members: [],
  }
}

afterEach(cleanup)

beforeEach(() => {
  vi.resetAllMocks()
  _idCounter = 0
})

describe('Dashboard', () => {
  it('shows loading skeleton initially', () => {
    vi.mocked(api.battleLogs.list).mockReturnValue(new Promise(() => {}))
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    expect(document.querySelectorAll('[data-testid="skeleton"]').length).toBeGreaterThan(0)
  })

  it('shows empty state when no battle logs exist', async () => {
    vi.mocked(api.battleLogs.list).mockResolvedValue([])
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await screen.findByText(/log your first battle/i)
  })

  it('shows error message when API fails', async () => {
    vi.mocked(api.battleLogs.list).mockRejectedValue(new Error('Network error'))
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await screen.findByText(/failed to load/i)
  })

  it('displays correct win rate', async () => {
    const logs = [
      ...Array.from({ length: 6 }, (_, i) => _makeLog('win', 'singles', i)),
      ...Array.from({ length: 3 }, (_, i) => _makeLog('loss', 'vgc', i + 6)),
      _makeLog('tie', 'singles', 9),
    ]
    vi.mocked(api.battleLogs.list).mockResolvedValue(logs)
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await screen.findByText('60%')
  })

  it('displays W/L/T counts', async () => {
    const logs = [
      ...Array.from({ length: 6 }, (_, i) => _makeLog('win', 'singles', i)),
      ...Array.from({ length: 3 }, (_, i) => _makeLog('loss', 'vgc', i + 6)),
      _makeLog('tie', 'singles', 9),
    ]
    vi.mocked(api.battleLogs.list).mockResolvedValue(logs)
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await waitFor(() => {
      expect(screen.getByText('6W')).toBeTruthy()
      expect(screen.getByText('3L')).toBeTruthy()
      expect(screen.getByText('1T')).toBeTruthy()
    })
  })

  it('displays correct format split', async () => {
    const logs = [
      ...Array.from({ length: 6 }, (_, i) => _makeLog('win', 'vgc', i)),
      ...Array.from({ length: 4 }, (_, i) => _makeLog('loss', 'singles', i + 6)),
    ]
    vi.mocked(api.battleLogs.list).mockResolvedValue(logs)
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await screen.findByText(/vgc 60%/i)
  })

  it('hides chart and shows threshold note when fewer than 10 battles', async () => {
    const logs = Array.from({ length: 9 }, (_, i) => _makeLog('win', 'singles', i))
    vi.mocked(api.battleLogs.list).mockResolvedValue(logs)
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await waitFor(() => {
      expect(screen.queryByTestId('line-chart')).toBeNull()
      expect(screen.getByText(/10 battles/i)).toBeTruthy()
    })
  })

  it('shows chart when 10 or more battles exist', async () => {
    const logs = Array.from({ length: 10 }, (_, i) => _makeLog('win', 'singles', i))
    vi.mocked(api.battleLogs.list).mockResolvedValue(logs)
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await screen.findByTestId('line-chart')
  })

  it('displays correct current streak', async () => {
    // 2 losses followed by 3 wins — most recent 3 are wins → streak = W3
    const logs = [
      _makeLog('loss', 'singles', 0),
      _makeLog('loss', 'singles', 1),
      _makeLog('win', 'singles', 2),
      _makeLog('win', 'singles', 3),
      _makeLog('win', 'singles', 4),
    ]
    vi.mocked(api.battleLogs.list).mockResolvedValue(logs)
    renderWithRouter(<Dashboard />, { route: '/dashboard', path: '/dashboard' })
    await screen.findByText('W3')
  })
})
