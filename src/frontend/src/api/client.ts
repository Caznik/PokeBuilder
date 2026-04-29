import type {
  PokemonList,
  PokemonDetail,
  AbilityDetail,
  CompetitiveSetResponse,
  GenerationConstraints,
  GenerationResponse,
  OptimizationResponse,
  ScoreResponse,
  TeamAnalysisResponse,
  TeamMemberInput,
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

export const api = {
  pokemon: {
    list: (page: number, pageSize: number, name?: string): Promise<PokemonList> => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      })
      if (name) params.set('name', name)
      return get<PokemonList>(`/pokemon/?${params}`)
    },
    getByName: (name: string): Promise<PokemonDetail> =>
      get<PokemonDetail>(`/pokemon/name/${encodeURIComponent(name)}`),
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
}
