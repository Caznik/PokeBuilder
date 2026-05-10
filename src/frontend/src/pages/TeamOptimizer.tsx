import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type {
  OptimizationResponse,
  CounterResponse,
  GenerationConstraints,
  TeamResult,
  Regulation,
  MetaPokemon,
} from '../api/types'
import TeamResultCard from '../components/TeamResultCard'
import PokemonTagInput from '../components/PokemonTagInput'

type Mode = 'general' | 'counter'

function parseNames(input: string): string[] {
  return input.split(',').map((s) => s.trim()).filter(Boolean)
}

export default function TeamOptimizer() {
  const [mode, setMode] = useState<Mode>('general')

  // GA state
  const [includeInput, setIncludeInput] = useState('')
  const [excludeInput, setExcludeInput] = useState('')
  const [regulationId, setRegulationId] = useState<number | null>(null)
  const [populationSize, setPopulationSize] = useState(50)
  const [generations, setGenerations] = useState(30)
  const [gaResult, setGaResult] = useState<OptimizationResponse | null>(null)

  // Counter state
  const [counterRegulationId, setCounterRegulationId] = useState<number | null>(null)
  const [counterResult, setCounterResult] = useState<CounterResponse | null>(null)

  const [regulations, setRegulations] = useState<Regulation[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.regulations.list()
      .then(setRegulations)
      .catch(() => { /* silently degrade */ })
  }, [])

  async function handleGaSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setGaResult(null)
    setLoading(true)
    const include = parseNames(includeInput)
    const exclude = parseNames(excludeInput)
    const constraints: GenerationConstraints = { include, exclude }
    if (regulationId !== null) constraints.regulation_id = regulationId
    try {
      const res = await api.team.optimize(
        include.length > 0 || exclude.length > 0 || regulationId !== null ? constraints : undefined,
        populationSize,
        generations,
      )
      setGaResult(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  async function handleCounterSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (counterRegulationId === null) {
      setError('Please select a regulation.')
      return
    }
    setError(null)
    setCounterResult(null)
    setLoading(true)
    try {
      const res = await api.team.counter(counterRegulationId)
      setCounterResult(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(team: TeamResult, name: string) {
    await api.savedTeams.save({
      name,
      score: team.score,
      breakdown: team.breakdown,
      members: team.members.map((m) => ({ pokemon_name: m.pokemon_name, set_id: m.set_id })),
      analysis: team.analysis,
    })
  }

  const sortedGaTeams = gaResult ? [...gaResult.best_teams].sort((a, b) => b.score - a.score) : []
  const sortedCounterTeams = counterResult ? [...counterResult.best_teams].sort((a, b) => b.score - a.score) : []

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Team Optimizer</h1>

      {/* Mode toggle */}
      <div className="flex gap-2 mb-6">
        {(['general', 'counter'] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => { setMode(m); setError(null) }}
            className="text-sm font-medium px-4 py-2 rounded transition-colors"
            style={{
              background: mode === m ? 'var(--accent)' : 'var(--surface)',
              color: mode === m ? 'var(--accent-fg)' : 'var(--text)',
              border: '1px solid var(--border)',
            }}
          >
            {m === 'general' ? 'General (GA)' : 'Counter Meta'}
          </button>
        ))}
      </div>

      {mode === 'general' && (
        <form onSubmit={handleGaSubmit} className="rounded-lg p-4 mb-6 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          {regulations.length > 0 && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">Format / Regulation</label>
              <select
                value={regulationId ?? ''}
                onChange={(e) => setRegulationId(e.target.value === '' ? null : Number(e.target.value))}
                className="w-full text-sm rounded px-3 py-2"
                style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)', colorScheme: 'dark' }}
              >
                <option value="">No regulation (all Pokémon)</option>
                {regulations.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </div>
          )}
          <PokemonTagInput label="Include Pokémon (comma-separated)" value={includeInput} onChange={setIncludeInput} placeholder="e.g. rillaboom, incineroar" />
          <PokemonTagInput label="Exclude Pokémon (comma-separated)" value={excludeInput} onChange={setExcludeInput} placeholder="e.g. wobbuffet" maxNames={Infinity} />
          <div>
            <label className="block text-xs text-gray-400 mb-1">Population Size: <span className="text-white">{populationSize}</span></label>
            <input type="range" min={10} max={100} step={10} value={populationSize} onChange={(e) => setPopulationSize(Number(e.target.value))} className="w-full" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Generations: <span className="text-white">{generations}</span></label>
            <input type="range" min={5} max={50} step={5} value={generations} onChange={(e) => setGenerations(Number(e.target.value))} className="w-full" />
          </div>
          <button type="submit" disabled={loading} className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
            {loading ? 'Running genetic algorithm…' : 'Run Optimizer'}
          </button>
        </form>
      )}

      {mode === 'counter' && (
        <form onSubmit={handleCounterSubmit} className="rounded-lg p-4 mb-6 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Suggests teams proven to beat the current meta based on real battle replays from Pokémon Showdown.
            Requires a regulation with ingested replay data.
          </p>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Regulation (required)</label>
            <select
              value={counterRegulationId ?? ''}
              onChange={(e) => setCounterRegulationId(e.target.value === '' ? null : Number(e.target.value))}
              className="w-full text-sm rounded px-3 py-2"
              style={{ background: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text)', colorScheme: 'dark' }}
            >
              <option value="">Select a regulation…</option>
              {regulations.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>
          <button type="submit" disabled={loading || counterRegulationId === null} className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}>
            {loading ? 'Analyzing meta…' : 'Find Counter Teams'}
          </button>
        </form>
      )}

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {mode === 'general' && gaResult && (
        <div>
          <p className="text-sm text-gray-400 mb-4">
            Ran <span className="text-white font-medium">{gaResult.generations_run}</span> generations,
            population <span className="text-white font-medium">{gaResult.initial_population}</span>,{' '}
            <span className="text-white font-medium">{gaResult.evaluations}</span> evaluations.
          </p>
          <div className="space-y-4">
            {sortedGaTeams.map((team, i) => (
              <TeamResultCard key={i} team={team} rank={i + 1} onSave={(name) => handleSave(team, name)} />
            ))}
          </div>
        </div>
      )}

      {mode === 'counter' && counterResult && (
        <div>
          <div className="rounded-lg p-4 mb-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
              Meta Snapshot — {counterResult.replays_analyzed} replays analyzed
            </p>
            <div className="flex flex-wrap gap-2">
              {counterResult.meta_snapshot.top_pokemon.map((p: MetaPokemon) => (
                <span
                  key={p.name}
                  className="text-xs px-2 py-1 rounded"
                  style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
                >
                  {p.name} <span style={{ color: 'var(--text-muted)' }}>{(p.usage_pct * 100).toFixed(1)}%</span>
                </span>
              ))}
            </div>
          </div>
          <div className="space-y-4">
            {sortedCounterTeams.map((team, i) => (
              <TeamResultCard key={i} team={team} rank={i + 1} onSave={(name) => handleSave(team, name)} />
            ))}
          </div>
          {sortedCounterTeams.length === 0 && (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              No valid counter teams found. Try ingesting more replay data for this regulation.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
