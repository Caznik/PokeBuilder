import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { api } from '../api/client'
import type {
  CompetitiveSet,
  ScoreResponse,
  TeamAnalysisResponse,
  SavedTeamMember,
  PokemonWithTypes,
} from '../api/types'
import ScoreBar from '../components/ScoreBar'
import BreakdownTable from '../components/BreakdownTable'
import AnalysisReport from '../components/AnalysisReport'
import TypeBadge from '../components/TypeBadge'

interface SlotState {
  pokemonName: string
  sets: CompetitiveSet[]
  selectedSetId: number | null
  setsLoading: boolean
  setsError: string | null
  pickerOpen: boolean
  pickerStep: 'browse' | 'detail'
  pickerPokemon: PokemonWithTypes | null
  pickerSearch: string
  pickerType: string | null
  pickerResults: PokemonWithTypes[]
  pickerLoading: boolean
}

function emptySlot(): SlotState {
  return {
    pokemonName: '', sets: [], selectedSetId: null, setsLoading: false, setsError: null,
    pickerOpen: false, pickerStep: 'browse', pickerPokemon: null,
    pickerSearch: '', pickerType: null, pickerResults: [], pickerLoading: false,
  }
}

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function StatBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min((value / 255) * 100, 100)
  const color =
    value >= 120 ? 'oklch(0.85 0.18 130)' :
    value >= 80  ? 'oklch(0.75 0.15 80)'  :
                   'oklch(0.60 0.12 25)'
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '36px 1fr 32px', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
        {label}
      </span>
      <div style={{ height: 5, borderRadius: 3, background: 'var(--surface)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width 0.2s' }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </span>
    </div>
  )
}

export default function TeamBuilder() {
  const location = useLocation()
  const [slots, setSlots] = useState<SlotState[]>(() => Array.from({ length: 6 }, emptySlot))
  const [allTypes, setAllTypes] = useState<string[]>([])
  const [scoreResult, setScoreResult] = useState<ScoreResponse | null>(null)
  const [analyzeResult, setAnalyzeResult] = useState<TeamAnalysisResponse | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const debounceTimers = useRef<Record<number, ReturnType<typeof setTimeout>>>({})
  const [teamName, setTeamName] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [savedSuccess, setSavedSuccess] = useState(false)

  useEffect(() => {
    api.types.list().then((types) => setAllTypes(types.map((t) => t.name)))
  }, [])

  async function loadSets(index: number, nameOverride: string, setIdOverride?: number) {
    const name = nameOverride.trim()
    if (!name) return
    updateSlot(index, { setsLoading: true, setsError: null, sets: [], selectedSetId: null, pokemonName: name })
    try {
      const res = await api.competitiveSets.get(name.toLowerCase())
      const autoSelect = setIdOverride ?? (res.sets.length === 1 ? res.sets[0].id : null)
      updateSlot(index, { sets: res.sets, selectedSetId: autoSelect, setsLoading: false })
    } catch (e: unknown) {
      updateSlot(index, { setsLoading: false, setsError: e instanceof Error ? e.message : 'Failed to load sets' })
    }
  }

  useEffect(() => {
    const state = location.state as { members?: SavedTeamMember[] } | null
    if (!state?.members?.length) return
    setSlots(() => Array.from({ length: 6 }, emptySlot))
    setScoreResult(null)
    setAnalyzeResult(null)
    setSubmitError(null)
    setSavedSuccess(false)
    state.members.forEach((m, i) => loadSets(i, m.pokemon_name, m.set_id))
  }, [location.key])

  function updateSlot(index: number, patch: Partial<SlotState>) {
    setSlots((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)))
  }

  async function fetchPickerResults(index: number, search: string, type: string | null) {
    updateSlot(index, { pickerLoading: true })
    try {
      const res = await api.pokemon.list(1, 20, search || undefined, type || undefined)
      updateSlot(index, { pickerResults: res.items, pickerLoading: false })
    } catch {
      updateSlot(index, { pickerLoading: false })
    }
  }

  function openPicker(index: number) {
    updateSlot(index, {
      pickerOpen: true, pickerStep: 'browse', pickerPokemon: null,
      pickerSearch: '', pickerType: null, pickerResults: [], pickerLoading: false,
    })
    fetchPickerResults(index, '', null)
  }

  function closePicker(index: number) {
    updateSlot(index, { pickerOpen: false })
  }

  function handlePickerSearch(index: number, value: string, currentType: string | null) {
    updateSlot(index, { pickerSearch: value })
    clearTimeout(debounceTimers.current[index])
    debounceTimers.current[index] = setTimeout(() => {
      fetchPickerResults(index, value, currentType)
    }, 300)
  }

  function handlePickerTypeToggle(index: number, type: string, currentSearch: string, currentType: string | null) {
    const newType = currentType === type ? null : type
    updateSlot(index, { pickerType: newType })
    fetchPickerResults(index, currentSearch, newType)
  }

  async function selectPokemon(index: number, pokemon: PokemonWithTypes) {
    updateSlot(index, { pickerStep: 'detail', pickerPokemon: pokemon, setsLoading: true, sets: [], selectedSetId: null, setsError: null })
    try {
      const res = await api.competitiveSets.get(pokemon.name.toLowerCase())
      const autoSelect = res.sets.length === 1 ? res.sets[0].id : null
      updateSlot(index, { sets: res.sets, selectedSetId: autoSelect, setsLoading: false })
    } catch (e: unknown) {
      updateSlot(index, { setsLoading: false, setsError: e instanceof Error ? e.message : 'Failed to load sets' })
    }
  }

  function confirmSlot(index: number) {
    setSlots((prev) => {
      const slot = prev[index]
      if (!slot.pickerPokemon || slot.selectedSetId === null) return prev
      return prev.map((s, i) =>
        i === index ? { ...s, pokemonName: slot.pickerPokemon!.name, pickerOpen: false } : s
      )
    })
  }

  function clearSlot(index: number) {
    setSlots((prev) => prev.map((s, i) => (i === index ? emptySlot() : s)))
    setScoreResult(null)
    setAnalyzeResult(null)
    setTeamName('')
    setSaveError(null)
    setSavedSuccess(false)
  }

  const allFilled = slots.every((s) => s.pokemonName && s.selectedSetId !== null)

  async function handleScore() {
    setSubmitting(true)
    setSubmitError(null)
    setScoreResult(null)
    setAnalyzeResult(null)
    setTeamName('')
    setSavedSuccess(false)
    setSaveError(null)
    try {
      const members = slots.map((s) => ({ pokemon_name: s.pokemonName, set_id: s.selectedSetId! }))
      setScoreResult(await api.team.score(members))
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleSave() {
    if (!scoreResult || !teamName.trim()) return
    setSaving(true)
    setSaveError(null)
    setSavedSuccess(false)
    try {
      const members = slots.map((s) => ({ pokemon_name: s.pokemonName, set_id: s.selectedSetId! }))
      await api.savedTeams.save({
        name: teamName.trim(),
        members,
        score: scoreResult.score,
        breakdown: scoreResult.breakdown,
        analysis: scoreResult.analysis,
      })
      setSavedSuccess(true)
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function handleAnalyze() {
    setSubmitting(true)
    setSubmitError(null)
    setScoreResult(null)
    setAnalyzeResult(null)
    try {
      const members = slots.map((s) => ({ pokemon_name: s.pokemonName, set_id: s.selectedSetId! }))
      setAnalyzeResult(await api.team.analyze(members))
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <div className="space-y-3 mb-6">
        {slots.map((slot, i) => (
          <div
            key={i}
            className="rounded-lg"
            style={{
              background: 'var(--surface)',
              border: `1px solid ${slot.pickerOpen ? 'var(--accent)' : 'var(--border)'}`,
            }}
          >
            {/* Slot header row */}
            <div className="flex items-center gap-2 p-3">
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', width: 16 }}>
                {i + 1}.
              </span>

              {slot.pokemonName ? (
                <>
                  <span className="text-sm font-medium flex-1" style={{ fontFamily: 'var(--font-mono)' }}>
                    {titleCase(slot.pokemonName)}
                  </span>
                  {slot.setsLoading && (
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>loading...</span>
                  )}
                  {slot.sets.length > 0 && (
                    <select
                      value={slot.selectedSetId ?? ''}
                      onChange={(e) => updateSlot(i, { selectedSetId: Number(e.target.value) })}
                      style={{
                        background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                        color: 'var(--text)', borderRadius: 4, padding: '2px 6px',
                        fontSize: 11, fontFamily: 'var(--font-mono)',
                      }}
                    >
                      <option value="">— set —</option>
                      {slot.sets.map((s) => (
                        <option key={s.id} value={s.id}>{s.name ?? `Set ${s.id}`}</option>
                      ))}
                    </select>
                  )}
                  <button
                    onClick={() => openPicker(i)}
                    style={{
                      fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                      letterSpacing: '0.06em', color: 'var(--accent)', background: 'none',
                      border: '1px solid var(--accent)', borderRadius: 4, padding: '2px 8px', cursor: 'pointer',
                    }}
                  >
                    Change
                  </button>
                  <button
                    onClick={() => clearSlot(i)}
                    style={{ fontSize: 14, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    ×
                  </button>
                </>
              ) : slot.pickerOpen ? (
                <>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', flex: 1 }}>Selecting Pokémon...</span>
                  <button
                    onClick={() => closePicker(i)}
                    style={{ fontSize: 14, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                  >
                    ×
                  </button>
                </>
              ) : (
                <button
                  onClick={() => openPicker(i)}
                  style={{
                    fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
                    background: 'none', border: '1px dashed var(--border)', borderRadius: 4,
                    padding: '3px 10px', cursor: 'pointer', flex: 1, textAlign: 'left',
                  }}
                >
                  + Add Pokémon
                </button>
              )}
            </div>

            {/* Inline picker */}
            {slot.pickerOpen && (
              <div style={{ borderTop: '1px solid var(--border)', padding: 12 }}>
                {slot.pickerStep === 'browse' ? (
                  <div className="space-y-3">
                    <input
                      autoFocus
                      type="text"
                      value={slot.pickerSearch}
                      onChange={(e) => handlePickerSearch(i, e.target.value, slot.pickerType)}
                      placeholder="Search Pokémon..."
                      style={{
                        width: '100%', background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                        color: 'var(--text)', borderRadius: 4, padding: '5px 10px',
                        fontSize: 12, fontFamily: 'var(--font-mono)',
                      }}
                    />
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {allTypes.map((t) => (
                        <button
                          key={t}
                          onClick={() => handlePickerTypeToggle(i, t, slot.pickerSearch, slot.pickerType)}
                          style={{
                            fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                            letterSpacing: '0.05em', borderRadius: 999, padding: '2px 8px',
                            cursor: 'pointer', border: 'none',
                            background: slot.pickerType === t ? 'var(--accent)' : 'var(--surface-2)',
                            color: slot.pickerType === t ? 'var(--accent-fg)' : 'var(--text-muted)',
                          }}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                    {slot.pickerLoading ? (
                      <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Loading...</p>
                    ) : (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 6 }}>
                        {slot.pickerResults.map((p) => (
                          <button
                            key={p.id}
                            onClick={() => selectPokemon(i, p)}
                            style={{
                              background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                              borderRadius: 6, padding: '8px 6px', cursor: 'pointer', textAlign: 'center',
                            }}
                          >
                            <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
                              {titleCase(p.name)}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: 3, flexWrap: 'wrap' }}>
                              {p.types.map((t) => (
                                <TypeBadge key={t.type_id} typeName={t.type_name} />
                              ))}
                            </div>
                          </button>
                        ))}
                        {slot.pickerResults.length === 0 && (
                          <p style={{ fontSize: 11, color: 'var(--text-muted)', gridColumn: '1 / -1' }}>
                            No Pokémon found.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  slot.pickerPokemon && (
                    <div className="space-y-3">
                      <button
                        onClick={() => updateSlot(i, { pickerStep: 'browse' })}
                        style={{
                          fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none',
                          cursor: 'pointer', fontFamily: 'var(--font-mono)', padding: 0,
                        }}
                      >
                        ← Back
                      </button>
                      <div>
                        <div className="text-base font-semibold mb-1">
                          {titleCase(slot.pickerPokemon.name)}
                        </div>
                        <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
                          {slot.pickerPokemon.types.map((t) => (
                            <TypeBadge key={t.type_id} typeName={t.type_name} />
                          ))}
                        </div>
                        <div className="space-y-1.5">
                          <StatBar label="HP"  value={slot.pickerPokemon.base_hp} />
                          <StatBar label="Atk" value={slot.pickerPokemon.base_attack} />
                          <StatBar label="Def" value={slot.pickerPokemon.base_defense} />
                          <StatBar label="SpA" value={slot.pickerPokemon.base_sp_attack} />
                          <StatBar label="SpD" value={slot.pickerPokemon.base_sp_defense} />
                          <StatBar label="Spe" value={slot.pickerPokemon.base_speed} />
                        </div>
                      </div>
                      <div>
                        <div style={{
                          fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                          letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 6,
                        }}>
                          Competitive Set
                        </div>
                        {slot.setsLoading ? (
                          <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Loading sets...</p>
                        ) : slot.setsError ? (
                          <p style={{ fontSize: 11, color: 'oklch(0.55 0.18 25)' }}>{slot.setsError}</p>
                        ) : slot.sets.length === 0 ? (
                          <p style={{ fontSize: 11, color: 'oklch(0.65 0.14 80)' }}>No sets available.</p>
                        ) : (
                          <select
                            value={slot.selectedSetId ?? ''}
                            onChange={(e) => updateSlot(i, { selectedSetId: Number(e.target.value) })}
                            style={{
                              width: '100%', background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                              color: 'var(--text)', borderRadius: 4, padding: '4px 8px',
                              fontSize: 12, fontFamily: 'var(--font-mono)',
                            }}
                          >
                            <option value="">— pick a set —</option>
                            {slot.sets.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.name ?? 'Unnamed set'} (ID: {s.id})
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                      <button
                        onClick={() => confirmSlot(i)}
                        disabled={slot.selectedSetId === null || slot.setsLoading}
                        style={{
                          fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                          letterSpacing: '0.06em', background: 'var(--accent)', color: 'var(--accent-fg)',
                          border: 'none', borderRadius: 4, padding: '5px 14px', cursor: 'pointer',
                          opacity: slot.selectedSetId === null || slot.setsLoading ? 0.4 : 1,
                        }}
                      >
                        Confirm
                      </button>
                    </div>
                  )
                )}
              </div>
            )}

            {slot.setsError && !slot.pickerOpen && (
              <p style={{ padding: '0 12px 8px', fontSize: 11, color: 'oklch(0.55 0.18 25)', margin: 0 }}>
                {slot.setsError}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={handleScore}
          disabled={!allFilled || submitting}
          className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors"
          style={{ background: 'var(--accent)', color: 'var(--accent-fg)' }}
        >
          {submitting ? 'Submitting...' : 'Score Team'}
        </button>
        <button
          onClick={handleAnalyze}
          disabled={!allFilled || submitting}
          className="disabled:opacity-40 text-sm font-medium px-4 py-2 rounded transition-colors"
          style={{ background: 'var(--surface-2)', color: 'var(--text)', border: '1px solid var(--border-subtle)' }}
        >
          {submitting ? 'Submitting...' : 'Analyze Only'}
        </button>
      </div>

      {submitError && <p className="text-red-400 text-sm mb-4">{submitError}</p>}

      {scoreResult && (
        <div className="rounded-lg p-4 space-y-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-4">
            <span className="font-medium" style={{ color: 'var(--text-muted)' }}>Team Score</span>
            <div className="flex-1">
              <ScoreBar score={scoreResult.score} maxScore={10} />
            </div>
          </div>
          <BreakdownTable breakdown={scoreResult.breakdown} />
          <AnalysisReport analysis={scoreResult.analysis} />
          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 12 }}>
            <div style={{
              fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
              letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 6,
            }}>
              Save Team
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="text"
                value={teamName}
                onChange={(e) => { setTeamName(e.target.value); setSavedSuccess(false) }}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSave() }}
                placeholder="Team name..."
                style={{
                  flex: 1, background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                  color: 'var(--text)', borderRadius: 4, padding: '5px 10px',
                  fontSize: 12, fontFamily: 'var(--font-mono)',
                }}
              />
              <button
                onClick={handleSave}
                disabled={!teamName.trim() || saving}
                style={{
                  fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                  letterSpacing: '0.06em', background: 'var(--accent)', color: 'var(--accent-fg)',
                  border: 'none', borderRadius: 4, padding: '5px 14px', cursor: 'pointer',
                  opacity: !teamName.trim() || saving ? 0.4 : 1,
                }}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
            {saveError && <p style={{ fontSize: 11, color: 'oklch(0.55 0.18 25)', marginTop: 6 }}>{saveError}</p>}
            {savedSuccess && <p style={{ fontSize: 11, color: 'oklch(0.75 0.18 140)', marginTop: 6 }}>Team saved!</p>}
          </div>
        </div>
      )}

      {analyzeResult && (
        <div className="rounded-lg p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <AnalysisReport analysis={analyzeResult} />
        </div>
      )}
    </div>
  )
}
