import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../test-utils'
import TeamBuilder from '../../pages/TeamBuilder'
import { api } from '../../api/client'
import type { PokemonWithTypes, CompetitiveSetResponse, ScoreResponse } from '../../api/types'

vi.mock('../../api/client', () => ({
  api: {
    types: { list: vi.fn() },
    pokemon: { list: vi.fn() },
    competitiveSets: { get: vi.fn() },
    team: { score: vi.fn(), analyze: vi.fn() },
    savedTeams: { save: vi.fn() },
    regulations: { list: vi.fn() },
  },
}))

const MOCK_PIKACHU: PokemonWithTypes = {
  id: 1,
  name: 'pikachu',
  generation: 1,
  base_hp: 35,
  base_attack: 55,
  base_defense: 40,
  base_sp_attack: 50,
  base_sp_defense: 50,
  base_speed: 90,
  types: [{ type_id: 13, type_name: 'electric' }],
}

const MOCK_SETS: CompetitiveSetResponse = {
  pokemon: 'pikachu',
  sets: [
    {
      id: 1,
      name: 'Standard',
      nature: 'timid',
      ability: 'static',
      item: 'light-ball',
      evs: { hp: 0, attack: 0, defense: 0, sp_attack: 252, sp_defense: 4, speed: 252 },
      moves: ['thunderbolt', 'volt-tackle', 'iron-tail', 'quick-attack'],
    },
  ],
}

const MOCK_SCORE: ScoreResponse = {
  score: 7.5,
  breakdown: {
    coverage:      { score: 8, reason: 'Good' },
    defensive:     { score: 7, reason: 'Good' },
    role:          { score: 8, reason: 'Good' },
    speed_control: { score: 7, reason: 'Good' },
    lead_pair:     { score: 8, reason: 'Good' },
  },
  analysis: {
    valid: true,
    issues: [],
    roles: {},
    weaknesses: {},
    resistances: {},
    coverage: { covered_types: [], missing_types: [] },
    speed_control_archetype: 'balanced',
  },
}

let user: ReturnType<typeof userEvent.setup>

beforeEach(() => {
  user = userEvent.setup()
  vi.resetAllMocks()
  vi.mocked(api.types.list).mockResolvedValue([])
  vi.mocked(api.regulations.list).mockResolvedValue([])
  vi.mocked(api.pokemon.list).mockResolvedValue({
    total: 1,
    page: 1,
    page_size: 20,
    items: [MOCK_PIKACHU],
  })
  vi.mocked(api.competitiveSets.get).mockResolvedValue(MOCK_SETS)
  vi.mocked(api.team.score).mockResolvedValue(MOCK_SCORE)
  vi.mocked(api.savedTeams.save).mockResolvedValue({
    id: 99,
    name: 'My Team',
    score: 7.5,
    created_at: '2026-01-01T00:00:00Z',
    regulation_id: null,
    members: [],
    breakdown: MOCK_SCORE.breakdown,
    analysis: MOCK_SCORE.analysis,
  })
})

afterEach(() => cleanup())

// Simulates the full picker flow for one slot:
// 1. Click first "+ Add Pokémon" button
// 2. Wait for Pikachu to appear in the browse grid, click it
// 3. Wait for Confirm to become enabled (auto-selected because only 1 set), click it
async function fillOneSlot() {
  const addBtn = screen.getAllByText('+ Add Pokémon')[0]
  await user.click(addBtn)
  const pikachuBtn = await screen.findByRole('button', { name: /pikachu/i })
  await user.click(pikachuBtn)
  const confirmBtn = await screen.findByRole('button', { name: /confirm/i })
  await user.click(confirmBtn)
}

describe('TeamBuilder', () => {
  it('renders 6 empty slots and a disabled Score Team button on initial load', async () => {
    renderWithRouter(<TeamBuilder />, { route: '/teams', path: '/teams' })
    const addButtons = await screen.findAllByText('+ Add Pokémon')
    expect(addButtons).toHaveLength(6)
    expect(screen.getByRole('button', { name: /score team/i })).toBeDisabled()
  })

  it('keeps Score Team disabled after filling only 1 slot', async () => {
    renderWithRouter(<TeamBuilder />, { route: '/teams', path: '/teams' })
    await screen.findAllByText('+ Add Pokémon')
    await fillOneSlot()
    expect(screen.getByRole('button', { name: /score team/i })).toBeDisabled()
  })

  it('enables Score Team after all 6 slots are filled', async () => {
    renderWithRouter(<TeamBuilder />, { route: '/teams', path: '/teams' })
    await screen.findAllByText('+ Add Pokémon')
    for (let i = 0; i < 6; i++) await fillOneSlot()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /score team/i })).not.toBeDisabled()
    )
  })

  it('calls api.team.score and shows score result after clicking Score Team', async () => {
    renderWithRouter(<TeamBuilder />, { route: '/teams', path: '/teams' })
    await screen.findAllByText('+ Add Pokémon')
    for (let i = 0; i < 6; i++) await fillOneSlot()

    await user.click(screen.getByRole('button', { name: /score team/i }))

    expect(vi.mocked(api.team.score)).toHaveBeenCalledOnce()
    await screen.findByText('Team Score')
    await screen.findByPlaceholderText('Team name...')
  })

  it('calls api.savedTeams.save and shows success after typing a name and saving', async () => {
    renderWithRouter(<TeamBuilder />, { route: '/teams', path: '/teams' })
    await screen.findAllByText('+ Add Pokémon')
    for (let i = 0; i < 6; i++) await fillOneSlot()
    await user.click(screen.getByRole('button', { name: /score team/i }))

    const nameInput = await screen.findByPlaceholderText('Team name...')
    await user.type(nameInput, 'My Team')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    await screen.findByText('Team saved!')
    expect(vi.mocked(api.savedTeams.save)).toHaveBeenCalledOnce()
  })

  it('shows an error message when the save API call fails', async () => {
    vi.mocked(api.savedTeams.save).mockRejectedValue(new Error('Server error'))

    renderWithRouter(<TeamBuilder />, { route: '/teams', path: '/teams' })
    await screen.findAllByText('+ Add Pokémon')
    for (let i = 0; i < 6; i++) await fillOneSlot()
    await user.click(screen.getByRole('button', { name: /score team/i }))

    const nameInput = await screen.findByPlaceholderText('Team name...')
    await user.type(nameInput, 'My Team')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    await screen.findByText('Server error')
  })
})
