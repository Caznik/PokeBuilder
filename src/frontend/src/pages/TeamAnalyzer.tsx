import { useState } from 'react'
import { api } from '../api/client'
import type {
  CompetitiveSet,
  ScoreResponse,
  TeamAnalysisResponse,
} from '../api/types'
import ScoreBar from '../components/ScoreBar'
import BreakdownTable from '../components/BreakdownTable'
import AnalysisReport from '../components/AnalysisReport'
import PokemonNameInput from '../components/PokemonNameInput'

interface SlotState {
  pokemonName: string
  sets: CompetitiveSet[]
  selectedSetId: number | null
  setsLoading: boolean
  setsError: string | null
}

function emptySlot(): SlotState {
  return { pokemonName: '', sets: [], selectedSetId: null, setsLoading: false, setsError: null }
}

function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

export default function TeamAnalyzer() {
  const [slots, setSlots] = useState<SlotState[]>(() => Array.from({ length: 6 }, emptySlot))
  const [nameInputs, setNameInputs] = useState<string[]>(() => Array(6).fill(''))
  const [scoreResult, setScoreResult] = useState<ScoreResponse | null>(null)
  const [analyzeResult, setAnalyzeResult] = useState<TeamAnalysisResponse | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  function updateSlot(index: number, patch: Partial<SlotState>) {
    setSlots((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)))
  }

  function updateNameInput(index: number, value: string) {
    setNameInputs((prev) => prev.map((v, i) => (i === index ? value : v)))
  }

  async function loadSets(index: number, nameOverride?: string) {
    const name = (nameOverride ?? nameInputs[index]).trim()
    if (!name) return
    updateSlot(index, { setsLoading: true, setsError: null, sets: [], selectedSetId: null, pokemonName: name })
    try {
      const res = await api.competitiveSets.get(name.toLowerCase())
      const autoSelect = res.sets.length === 1 ? res.sets[0].id : null
      updateSlot(index, { sets: res.sets, selectedSetId: autoSelect, setsLoading: false })
    } catch (e: unknown) {
      updateSlot(index, {
        setsLoading: false,
        setsError: e instanceof Error ? e.message : 'Failed to load sets',
      })
    }
  }

  function clearSlot(index: number) {
    updateSlot(index, emptySlot())
    updateNameInput(index, '')
  }

  const allFilled = slots.every((s) => s.pokemonName && s.selectedSetId !== null)

  async function handleScore() {
    setSubmitting(true)
    setSubmitError(null)
    setScoreResult(null)
    setAnalyzeResult(null)
    try {
      const members = slots.map((s) => ({ pokemon_name: s.pokemonName, set_id: s.selectedSetId! }))
      const res = await api.team.score(members)
      setScoreResult(res)
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAnalyze() {
    setSubmitting(true)
    setSubmitError(null)
    setScoreResult(null)
    setAnalyzeResult(null)
    try {
      const members = slots.map((s) => ({ pokemon_name: s.pokemonName, set_id: s.selectedSetId! }))
      const res = await api.team.analyze(members)
      setAnalyzeResult(res)
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Team Analyzer</h1>
      <p className="text-sm text-gray-400 mb-5">
        Load 6 Pokémon by name, pick a competitive set for each, then score or analyze the team.
      </p>

      {/* 6 slots */}
      <div className="space-y-3 mb-6">
        {slots.map((slot, i) => (
          <div key={i} className="rounded-lg p-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-gray-500 w-5">{i + 1}.</span>
              <PokemonNameInput
                value={nameInputs[i]}
                onChange={(v) => updateNameInput(i, v)}
                onSelect={(name) => loadSets(i, name)}
                placeholder="Pokémon name"
                className="w-full rounded px-3 py-1.5 text-sm placeholder-gray-500"
              />
              <button
                onClick={() => loadSets(i)}
                disabled={slot.setsLoading || !nameInputs[i].trim()}
                className="disabled:opacity-40 text-xs px-3 py-1.5 rounded transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
              >
                {slot.setsLoading ? '...' : 'Load'}
              </button>
              <button
                onClick={() => clearSlot(i)}
                className="text-gray-500 hover:text-gray-300 text-xs px-2 py-1.5"
              >
                ×
              </button>
            </div>

            {slot.setsError && (
              <p className="text-red-400 text-xs ml-7">{slot.setsError}</p>
            )}

            {slot.sets.length > 0 && (
              <div className="flex items-center gap-2 ml-7">
                <span className="text-xs text-gray-400">{titleCase(slot.pokemonName)}</span>
                <select
                  value={slot.selectedSetId ?? ''}
                  onChange={(e) => updateSlot(i, { selectedSetId: Number(e.target.value) })}
                  className="flex-1 rounded px-2 py-1 text-xs" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)', color: 'var(--text)', fontFamily: 'var(--font-mono)' }}
                >
                  <option value="">— pick a set —</option>
                  {slot.sets.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name ?? `Unnamed set`} (ID: {s.id})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {slot.pokemonName && slot.sets.length === 0 && !slot.setsLoading && !slot.setsError && (
              <p className="text-yellow-600 text-xs ml-7">No sets available — cannot score this Pokémon.</p>
            )}
          </div>
        ))}
      </div>

      {/* Submit buttons */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={handleScore}
          disabled={!allFilled || submitting}
          className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors" style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
        >
          {submitting ? 'Submitting...' : 'Score Team'}
        </button>
        <button
          onClick={handleAnalyze}
          disabled={!allFilled || submitting}
          className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors" style={{ background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border-subtle)' }}
        >
          {submitting ? 'Submitting...' : 'Analyze Only'}
        </button>
      </div>

      {submitError && <p className="text-red-400 text-sm mb-4">{submitError}</p>}

      {/* Score result */}
      {scoreResult && (
        <div className="rounded-lg p-4 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-4">
            <span className="text-gray-400 font-medium">Team Score</span>
            <div className="flex-1">
              <ScoreBar score={scoreResult.score} maxScore={10} />
            </div>
          </div>
          <BreakdownTable breakdown={scoreResult.breakdown} />
          <AnalysisReport analysis={scoreResult.analysis} />
        </div>
      )}

      {/* Analyze only result */}
      {analyzeResult && (
        <div className="rounded-lg p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <AnalysisReport analysis={analyzeResult} />
        </div>
      )}
    </div>
  )
}
