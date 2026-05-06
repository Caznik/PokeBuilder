import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../test-utils'
import Teams from '../../pages/Teams'
import { api } from '../../api/client'
import type { SavedTeamSummary, PokemonDetail } from '../../api/types'

vi.mock('../../api/client', () => ({
  api: {
    types: { list: vi.fn() },
    pokemon: { list: vi.fn(), getByName: vi.fn() },
    savedTeams: { list: vi.fn(), delete: vi.fn(), get: vi.fn(), save: vi.fn() },
    competitiveSets: { get: vi.fn() },
    team: { score: vi.fn(), analyze: vi.fn() },
  },
}))

const MOCK_MEMBER = (slot: number) => ({
  slot,
  pokemon_name: 'pikachu',
  set_id: 1,
  set_name: 'Standard',
  nature: 'timid',
  ability: 'static',
  item: 'light-ball',
  tera_type: null,
  evs: null,
  moves: null,
})

const MOCK_TEAM_SUMMARY: SavedTeamSummary = {
  id: 1,
  name: 'Test Team',
  score: 7.5,
  created_at: '2026-01-01T00:00:00Z',
  members: [1, 2, 3, 4, 5, 6].map(MOCK_MEMBER),
}

const MOCK_POKEMON_DETAIL: PokemonDetail = {
  id: 1,
  name: 'pikachu',
  generation: 1,
  base_hp: 35,
  base_attack: 55,
  base_defense: 40,
  base_sp_attack: 50,
  base_sp_defense: 50,
  base_speed: 90,
  abilities: [{ ability_id: 1, ability_name: 'static', is_hidden: false }],
  types: [{ type_id: 13, type_name: 'electric' }],
}

let user: ReturnType<typeof userEvent.setup>

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  vi.resetAllMocks()
  user = userEvent.setup()
  vi.mocked(api.types.list).mockResolvedValue([])
  vi.mocked(api.pokemon.list).mockResolvedValue({ total: 0, items: [], page: 1, page_size: 20 })
  vi.mocked(api.pokemon.getByName).mockResolvedValue(MOCK_POKEMON_DETAIL)
  vi.mocked(api.savedTeams.list).mockResolvedValue([])
  vi.mocked(api.savedTeams.delete).mockResolvedValue(undefined)
})

describe('Teams — saved tab', () => {
  it('renders saved team names', async () => {
    vi.mocked(api.savedTeams.list).mockResolvedValue([MOCK_TEAM_SUMMARY])
    renderWithRouter(<Teams />, { route: '/teams?tab=saved', path: '/teams' })
    await screen.findByText('Test Team')
  })

  it('shows empty-state message when no teams are saved', async () => {
    renderWithRouter(<Teams />, { route: '/teams?tab=saved', path: '/teams' })
    await screen.findByText(/no saved teams yet/i)
  })

  it('removes team from list after delete is confirmed', async () => {
    // First call returns the team; subsequent calls (triggered by tab re-mounts) return empty
    vi.mocked(api.savedTeams.list)
      .mockResolvedValueOnce([MOCK_TEAM_SUMMARY])
      .mockResolvedValue([])
    renderWithRouter(<Teams />, { route: '/teams?tab=saved', path: '/teams' })
    await screen.findByText('Test Team')

    const deleteButton = screen.getAllByTitle('Delete team')[0]
    await user.click(deleteButton)
    await screen.findByText('Delete?')
    await user.click(screen.getByText('Yes'))

    await waitFor(() =>
      expect(vi.mocked(api.savedTeams.delete)).toHaveBeenCalledWith(1)
    )
    await screen.findByText(/no saved teams yet/i)
    expect(screen.queryByText('Test Team')).not.toBeInTheDocument()
  })
})
