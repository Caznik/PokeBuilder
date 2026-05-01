import { useState } from 'react'
import { api } from '../api/client'
import type { OptimizationResponse, GenerationConstraints, TeamResult } from '../api/types'
import TeamResultCard from '../components/TeamResultCard'
import PokemonTagInput from '../components/PokemonTagInput'

function parseNames(input: string): string[] {
  return input.split(',').map((s) => s.trim()).filter(Boolean)
}

export default function TeamOptimizer() {
  const [includeInput, setIncludeInput] = useState('')
  const [excludeInput, setExcludeInput] = useState('')
  const [populationSize, setPopulationSize] = useState(50)
  const [generations, setGenerations] = useState(30)
  const [result, setResult] = useState<OptimizationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setResult(null)
    setLoading(true)

    const include = parseNames(includeInput)
    const exclude = parseNames(excludeInput)
    const constraints: GenerationConstraints | undefined =
      include.length > 0 || exclude.length > 0 ? { include, exclude } : undefined

    try {
      const res = await api.team.optimize(constraints, populationSize, generations)
      setResult(res)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const sortedTeams = result
    ? [...result.best_teams].sort((a, b) => b.score - a.score)
    : []

  async function handleSave(team: TeamResult, name: string) {
    await api.savedTeams.save({
      name,
      score: team.score,
      breakdown: team.breakdown,
      members: team.members.map((m) => ({ pokemon_name: m.pokemon_name, set_id: m.set_id })),
      analysis: team.analysis,
    })
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Team Optimizer</h1>

      <form onSubmit={handleSubmit} className="rounded-lg p-4 mb-6 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <PokemonTagInput
          label="Include Pokémon (comma-separated)"
          value={includeInput}
          onChange={setIncludeInput}
          placeholder="e.g. rillaboom, incineroar"
        />
        <PokemonTagInput
          label="Exclude Pokémon (comma-separated)"
          value={excludeInput}
          onChange={setExcludeInput}
          placeholder="e.g. wobbuffet"
          maxNames={Infinity}
        />

        {/* Population size slider */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">
            Population Size: <span className="text-white">{populationSize}</span>
          </label>
          <input
            type="range"
            min={10} max={100} step={10}
            value={populationSize}
            onChange={(e) => setPopulationSize(Number(e.target.value))}
            className="w-full"
          />
        </div>

        {/* Generations slider */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">
            Generations: <span className="text-white">{generations}</span>
          </label>
          <input
            type="range"
            min={5} max={50} step={5}
            value={generations}
            onChange={(e) => setGenerations(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
        >
          {loading ? 'Running genetic algorithm... this may take a few seconds.' : 'Run Optimizer'}
        </button>
      </form>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {result && (
        <div>
          <p className="text-sm text-gray-400 mb-4">
            Ran <span className="text-white font-medium">{result.generations_run}</span> generations,
            population <span className="text-white font-medium">{result.initial_population}</span>,{' '}
            <span className="text-white font-medium">{result.evaluations}</span> evaluations.
          </p>
          <div className="space-y-4">
            {sortedTeams.map((team, i) => (
              <TeamResultCard
                key={i}
                team={team}
                rank={i + 1}
                onSave={(name) => handleSave(team, name)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
