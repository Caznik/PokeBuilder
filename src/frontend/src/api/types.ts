// Pokémon
export interface Pokemon {
  id: number
  name: string
  generation: number | null
  base_hp: number
  base_attack: number
  base_defense: number
  base_sp_attack: number
  base_sp_defense: number
  base_speed: number
}

export interface PokemonAbility {
  ability_id: number
  ability_name: string
  is_hidden: boolean
}

export interface AbilityDetail {
  id: number
  name: string
  description: string | null
}

export interface PokemonType {
  type_id: number
  type_name: string
}

export interface PokemonDetail extends Pokemon {
  abilities: PokemonAbility[]
  types: PokemonType[]
}

export interface PokemonWithTypes extends Pokemon {
  types: PokemonType[]
}

export interface PokemonList {
  total: number
  items: PokemonWithTypes[]
  page: number
  page_size: number
}

export interface TypeListItem {
  id: number
  name: string
}

// Competitive sets
export interface CompetitiveSetEvs {
  hp: number
  attack: number
  defense: number
  sp_attack: number
  sp_defense: number
  speed: number
}

export interface CompetitiveSet {
  id: number
  name: string | null
  nature: string | null
  ability: string | null
  item: string | null
  evs: CompetitiveSetEvs
  moves: string[]
}

export interface CompetitiveSetResponse {
  pokemon: string
  sets: CompetitiveSet[]
}

// Scoring & analysis
export interface ScoreComponent {
  score: number
  reason: string
}

export interface ScoreBreakdown {
  coverage: ScoreComponent
  defensive: ScoreComponent
  role: ScoreComponent
  speed_control: ScoreComponent
  lead_pair: ScoreComponent
}

export interface CoverageResult {
  covered_types: string[]
  missing_types: string[]
}

export interface TeamAnalysisResponse {
  valid: boolean
  issues: string[]
  roles: Record<string, number>
  weaknesses: Record<string, number>
  resistances: Record<string, number>
  coverage: CoverageResult
  speed_control_archetype: string
}

export interface ScoreResponse {
  score: number
  breakdown: ScoreBreakdown
  analysis: TeamAnalysisResponse
}

// Generation & optimization
export interface TeamMemberInput {
  pokemon_name: string
  set_id: number
}

export interface GenerationMember {
  pokemon_name: string
  set_id: number
  set_name: string | null
  nature: string | null
  ability: string | null
}

export interface TeamResult {
  score: number
  breakdown: ScoreBreakdown
  members: GenerationMember[]
  analysis: TeamAnalysisResponse
}

export interface GenerationConstraints {
  include: string[]
  exclude: string[]
}

export interface GenerationResponse {
  teams: TeamResult[]
  generated: number
  valid_found: number
}

export interface OptimizationResponse {
  best_teams: TeamResult[]
  generations_run: number
  initial_population: number
  evaluations: number
}

// Saved teams
export interface SavedTeamMember {
  slot: number
  pokemon_name: string
  set_id: number
  set_name: string | null
  nature: string | null
  ability: string | null
}

export interface SavedTeamSummary {
  id: number
  name: string
  score: number
  created_at: string
  members: SavedTeamMember[]
}

export interface SavedTeamDetail extends SavedTeamSummary {
  breakdown: ScoreBreakdown
  analysis: TeamAnalysisResponse
}

export interface SaveTeamRequest {
  name: string
  members: TeamMemberInput[]
  score: number
  breakdown: ScoreBreakdown
  analysis: TeamAnalysisResponse
}

export interface UpdateTeamRequest {
  name?: string
  score?: number
  breakdown?: ScoreBreakdown
  analysis?: TeamAnalysisResponse
}

export interface UpdateMemberRequest {
  pokemon_name: string
  set_id: number
}
