import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TeamResultCard from '../../components/TeamResultCard'
import type { TeamResult } from '../../api/types'

vi.mock('../../components/SetDetailModal', () => ({
  default: ({ member, onClose }: { member: { pokemon_name: string }; onClose: () => void }) => (
    <div data-testid="set-detail-modal">
      <span>Modal for {member.pokemon_name}</span>
      <button onClick={onClose}>close-modal</button>
    </div>
  ),
}))

const mockTeam: TeamResult = {
  score: 7.4,
  breakdown: {
    coverage:      { score: 0.8, reason: 'ok' },
    defensive:     { score: 0.7, reason: 'ok' },
    role:          { score: 0.9, reason: 'ok' },
    speed_control: { score: 0.6, reason: 'ok' },
    lead_pair:     { score: 0.8, reason: 'ok' },
  },
  members: [
    { pokemon_name: 'incineroar',   set_id: 3,  set_name: 'Careful', nature: 'careful', ability: 'intimidate' },
    { pokemon_name: 'garchomp',     set_id: 5,  set_name: null,      nature: 'jolly',   ability: 'rough-skin' },
    { pokemon_name: 'flutter-mane', set_id: 7,  set_name: null,      nature: 'timid',   ability: 'protosynthesis' },
    { pokemon_name: 'farigiraf',    set_id: 9,  set_name: null,      nature: 'sassy',   ability: 'cud-chew' },
    { pokemon_name: 'kingambit',    set_id: 11, set_name: null,      nature: 'adamant', ability: 'supreme-overlord' },
    { pokemon_name: 'sneasler',     set_id: 13, set_name: null,      nature: 'jolly',   ability: 'unburden' },
  ],
  analysis: {
    valid: true, issues: [], roles: {}, weaknesses: {}, resistances: {},
    coverage: { covered_types: [], missing_types: [] },
    speed_control_archetype: 'none',
  },
}

describe('TeamResultCard', () => {
  afterEach(cleanup)

  it('renders all member pokemon names', () => {
    render(<TeamResultCard team={mockTeam} rank={1} />)
    expect(screen.getByText('Incineroar')).toBeInTheDocument()
    expect(screen.getByText('Garchomp')).toBeInTheDocument()
  })

  it('clicking a member chip opens SetDetailModal for that pokemon', async () => {
    render(<TeamResultCard team={mockTeam} rank={1} />)
    await userEvent.click(screen.getByRole('button', { name: /incineroar/i }))
    expect(screen.getByTestId('set-detail-modal')).toBeInTheDocument()
    expect(screen.getByText('Modal for incineroar')).toBeInTheDocument()
  })

  it('closing the modal removes it', async () => {
    render(<TeamResultCard team={mockTeam} rank={1} />)
    await userEvent.click(screen.getByRole('button', { name: /incineroar/i }))
    await userEvent.click(screen.getByText('close-modal'))
    expect(screen.queryByTestId('set-detail-modal')).not.toBeInTheDocument()
  })

  it('clicking a different chip switches the modal to that pokemon', async () => {
    render(<TeamResultCard team={mockTeam} rank={1} />)
    await userEvent.click(screen.getByRole('button', { name: /incineroar/i }))
    expect(screen.getByText('Modal for incineroar')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /garchomp/i }))
    expect(screen.getByText('Modal for garchomp')).toBeInTheDocument()
    expect(screen.queryByText('Modal for incineroar')).not.toBeInTheDocument()
  })
})
