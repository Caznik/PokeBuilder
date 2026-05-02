import type {
  PokemonList,
  PokemonWithTypes,
  PokemonDetail,
  AbilityDetail,
  TypeListItem,
  CompetitiveSetResponse,
  GenerationConstraints,
  GenerationResponse,
  OptimizationResponse,
  ScoreResponse,
  TeamAnalysisResponse,
  TeamMemberInput,
  SavedTeamSummary,
  SavedTeamDetail,
  SaveTeamRequest,
  UpdateTeamRequest,
  UpdateMemberRequest,
  PokemonMovesResponse,
} from './types'

const BASE = '/api'

async function extractError(res: Response): Promise<Error> {
  try {
    const json = await res.json() as { detail?: string }
    if (json.detail) return new Error(json.detail)
  } catch { /* fall through */ }
  return new Error(`${res.status} ${res.statusText}`)
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw await extractError(res)
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await extractError(res)
  return res.json() as Promise<T>
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await extractError(res)
  return res.json() as Promise<T>
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw await extractError(res)
}

export const api = {
  pokemon: {
    list: (page: number, pageSize: number, name?: string, type?: string): Promise<PokemonList> => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
      if (name) params.set('name', name)
      if (type) params.set('type', type)
      return get<PokemonList>(`/pokemon/?${params}`)
    },
    getByName: (name: string): Promise<PokemonDetail> =>
      get<PokemonDetail>(`/pokemon/name/${encodeURIComponent(name)}`),
  },

  types: {
    list: (): Promise<TypeListItem[]> =>
      get<TypeListItem[]>('/types/'),
  },

  abilities: {
    getByName: (name: string): Promise<AbilityDetail> =>
      get<AbilityDetail>(`/abilities/name/${encodeURIComponent(name)}`),
  },

  competitiveSets: {
    get: (name: string): Promise<CompetitiveSetResponse> =>
      get<CompetitiveSetResponse>(`/competitive-sets/${encodeURIComponent(name)}`),
  },

  team: {
    generate: (constraints?: GenerationConstraints): Promise<GenerationResponse> =>
      post<GenerationResponse>('/team/generate', { constraints }),

    optimize: (
      constraints?: GenerationConstraints,
      populationSize?: number,
      generations?: number,
    ): Promise<OptimizationResponse> =>
      post<OptimizationResponse>('/team/optimize', {
        constraints,
        population_size: populationSize,
        generations,
      }),

    score: (members: TeamMemberInput[]): Promise<ScoreResponse> =>
      post<ScoreResponse>('/team/score', members),

    analyze: (members: TeamMemberInput[]): Promise<TeamAnalysisResponse> =>
      post<TeamAnalysisResponse>('/team/analyze', members),
  },

  savedTeams: {
    list: (): Promise<SavedTeamSummary[]> =>
      get<SavedTeamSummary[]>('/saved-teams/'),

    get: (id: number): Promise<SavedTeamDetail> =>
      get<SavedTeamDetail>(`/saved-teams/${id}`),

    save: (payload: SaveTeamRequest): Promise<SavedTeamDetail> =>
      post<SavedTeamDetail>('/saved-teams/', payload),

    update: (id: number, payload: UpdateTeamRequest): Promise<SavedTeamDetail> =>
      patch<SavedTeamDetail>(`/saved-teams/${id}`, payload),

    updateMember: (id: number, slot: number, member: UpdateMemberRequest): Promise<SavedTeamDetail> =>
      patch<SavedTeamDetail>(`/saved-teams/${id}/members/${slot}`, member),

    delete: (id: number): Promise<void> =>
      del(`/saved-teams/${id}`),
  },

  moves: {
    forPokemon: (pokemonId: number): Promise<PokemonMovesResponse> =>
      get<PokemonMovesResponse>(`/moves/pokemon/${pokemonId}/moves`),
  },
}
