import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SetDetailModal from '../../components/SetDetailModal'
import type { GenerationMember } from '../../api/types'

vi.mock('../../api/client', () => ({
  api: {
    pokemon: {
      getByName: vi.fn(),
    },
    competitiveSets: {
      get: vi.fn(),
    },
  },
}))

import { api } from '../../api/client'

const mockMember: GenerationMember = {
  pokemon_name: 'incineroar',
  set_id: 3,
  set_name: 'Careful Incineroar',
  nature: 'careful',
  ability: 'intimidate',
}

const mockPokemon = {
  id: 727,
  name: 'incineroar',
  generation: 7,
  base_hp: 95,
  base_attack: 115,
  base_defense: 90,
  base_sp_attack: 80,
  base_sp_defense: 90,
  base_speed: 60,
  types: [
    { type_id: 10, type_name: 'fire' },
    { type_id: 17, type_name: 'dark' },
  ],
  abilities: [],
}

const mockSet = {
  id: 3,
  name: 'Careful Incineroar',
  nature: 'careful',
  ability: 'intimidate',
  item: 'Safety Goggles',
  evs: { hp: 252, attack: 0, defense: 4, sp_attack: 0, sp_defense: 252, speed: 0 },
  moves: ['fake-out', 'flare-blitz', 'parting-shot', 'knock-off'],
}

describe('SetDetailModal', () => {
  const onClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(cleanup)

  it('shows loading state while fetching', () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('shows error when either fetch fails', async () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('fail'))
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('fail'))
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    await waitFor(() =>
      expect(screen.getByText('Could not load set details.')).toBeInTheDocument()
    )
  })

  it('renders all four move names after a successful fetch', async () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockResolvedValue(mockPokemon)
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      pokemon: 'incineroar',
      sets: [mockSet],
    })
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    await waitFor(() => expect(screen.getByText('fake-out')).toBeInTheDocument())
    expect(screen.getByText('flare-blitz')).toBeInTheDocument()
    expect(screen.getByText('parting-shot')).toBeInTheDocument()
    expect(screen.getByText('knock-off')).toBeInTheDocument()
  })

  it('renders the item after a successful fetch', async () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockResolvedValue(mockPokemon)
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      pokemon: 'incineroar',
      sets: [mockSet],
    })
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    await waitFor(() => expect(screen.getByText('Safety Goggles')).toBeInTheDocument())
  })

  it('calls onClose when Escape is pressed', async () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when the Close button is clicked', async () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: 'Close' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('calls onClose when the backdrop is clicked', async () => {
    ;(api.pokemon.getByName as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    ;(api.competitiveSets.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    render(<SetDetailModal member={mockMember} onClose={onClose} />)
    await userEvent.click(screen.getByTestId('modal-backdrop'))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
