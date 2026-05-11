import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { cleanup } from '@testing-library/react'
import { renderWithRouter } from '../test-utils'
import TeamDetail from '../../pages/TeamDetail'
import { api } from '../../api/client'
import type { SavedTeamDetail, PokemonDetail } from '../../api/types'

vi.mock('../../api/client', () => ({
  api: {
    savedTeams: { get: vi.fn(), update: vi.fn() },
    pokemon: { getByName: vi.fn() },
    moves: { forPokemon: vi.fn() },
  },
}))

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

const MOCK_TEAM_DETAIL: SavedTeamDetail = {
  id: 1,
  name: 'Test Team',
  score: 7.5,
  created_at: '2026-01-01T00:00:00Z',
  regulation_id: null,
  members: [1, 2, 3, 4, 5, 6].map(MOCK_MEMBER),
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
  vi.mocked(api.savedTeams.get).mockResolvedValue(MOCK_TEAM_DETAIL)
  vi.mocked(api.pokemon.getByName).mockResolvedValue(MOCK_POKEMON_DETAIL)
  vi.mocked(api.moves.forPokemon).mockResolvedValue({ pokemon_id: 1, pokemon_name: 'pikachu', moves: [] })
})

afterEach(() => cleanup())

describe('TeamDetail', () => {
  it('renders all 6 Pokémon slot names after loading', async () => {
    renderWithRouter(<TeamDetail />, { route: '/teams/1', path: '/teams/:id' })
    const names = await screen.findAllByText('Pikachu')
    expect(names.length).toBe(6)
  })

  it('opens MemberDetailModal when a slot card is clicked', async () => {
    renderWithRouter(<TeamDetail />, { route: '/teams/1', path: '/teams/:id' })

    // Wait for "electric" TypeBadges — confirms pokemonMap is populated
    // (the modal returns null until pokemonMap has the entry)
    // There are 6 slots all showing electric, so use findAllByText
    await screen.findAllByText('electric')

    // Click the first slot card's name text — bubbles up to parent div's onClick
    const slotNames = screen.getAllByText('Pikachu')
    await user.click(slotNames[0])

    // MemberDetailModal renders a "Nature" section label when mounted
    await screen.findByText('Nature')
  })
})
