import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { SavedTeamDetail, PokemonDetail } from '../api/types'
import ScoreBar from '../components/ScoreBar'
import BreakdownTable from '../components/BreakdownTable'
import AnalysisReport from '../components/AnalysisReport'
import TypeBadge from '../components/TypeBadge'

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function spriteUrl(name: string) {
  return `https://img.pokemondb.net/sprites/home/normal/${name}.png`
}

export default function TeamDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [team, setTeam] = useState<SavedTeamDetail | null>(null)
  const [pokemonMap, setPokemonMap] = useState<Record<string, PokemonDetail>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [editingName, setEditingName] = useState(false)
  const [nameValue, setNameValue] = useState('')
  const [nameSaving, setNameSaving] = useState(false)
  const [nameError, setNameError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api.savedTeams.get(Number(id))
      .then(async (t) => {
        setTeam(t)
        setNameValue(t.name)
        const results = await Promise.allSettled(
          t.members.map((m) => api.pokemon.getByName(m.pokemon_name))
        )
        const map: Record<string, PokemonDetail> = {}
        results.forEach((r) => {
          if (r.status === 'fulfilled') map[r.value.name] = r.value
        })
        setPokemonMap(map)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load team'))
      .finally(() => setLoading(false))
  }, [id])

  async function handleRename() {
    if (!team || !nameValue.trim()) return
    setNameSaving(true)
    setNameError(null)
    try {
      const updated = await api.savedTeams.update(team.id, { name: nameValue.trim() })
      setTeam(updated)
      setEditingName(false)
    } catch (e: unknown) {
      setNameError(e instanceof Error ? e.message : 'Failed to rename')
    } finally {
      setNameSaving(false)
    }
  }

  function handleLoad() {
    if (!team) return
    const members = [...team.members]
      .sort((a, b) => a.slot - b.slot)
      .map((m) => ({ pokemon_name: m.pokemon_name, set_id: m.set_id }))
    navigate({ pathname: '/teams', search: '' }, { state: { members } })
  }

  if (loading) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading...</p>
  if (error || !team) return <p style={{ color: 'oklch(0.55 0.18 25)', fontSize: 13 }}>{error ?? 'Team not found'}</p>

  return (
    <div>
      <button
        onClick={() => navigate({ pathname: '/teams', search: '?tab=saved' })}
        style={{
          fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none',
          cursor: 'pointer', fontFamily: 'var(--font-mono)', padding: 0, marginBottom: 16,
        }}
      >
        ← My Teams
      </button>

      <div className="flex items-center gap-4 mb-6">
        <div style={{ flex: 1 }}>
          {editingName ? (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                autoFocus
                type="text"
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename()
                  if (e.key === 'Escape') { setEditingName(false); setNameValue(team.name) }
                }}
                style={{
                  background: 'var(--surface-2)', border: '1px solid var(--accent)',
                  color: 'var(--text)', borderRadius: 4, padding: '4px 8px',
                  fontSize: 18, fontFamily: 'var(--font-mono)', fontWeight: 700,
                }}
              />
              <button
                onClick={handleRename}
                disabled={nameSaving || !nameValue.trim()}
                style={{
                  fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                  background: 'var(--accent)', color: 'var(--accent-fg)',
                  border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer',
                  opacity: nameSaving || !nameValue.trim() ? 0.4 : 1,
                }}
              >
                {nameSaving ? '...' : 'Save'}
              </button>
              <button
                onClick={() => { setEditingName(false); setNameValue(team.name) }}
                style={{ fontSize: 14, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                ×
              </button>
            </div>
          ) : (
            <h1
              className="text-xl font-bold cursor-pointer"
              onClick={() => setEditingName(true)}
              title="Click to rename"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              {team.name}
            </h1>
          )}
          {nameError && <p style={{ fontSize: 11, color: 'oklch(0.55 0.18 25)', marginTop: 4 }}>{nameError}</p>}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            {new Date(team.created_at).toLocaleDateString()}
          </div>
        </div>
        <div style={{ width: 200 }}>
          <ScoreBar score={team.score} maxScore={10} />
        </div>
        <button
          onClick={handleLoad}
          style={{
            fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
            letterSpacing: '0.06em', background: 'var(--accent)', color: 'var(--accent-fg)',
            border: 'none', borderRadius: 4, padding: '6px 16px', cursor: 'pointer',
          }}
        >
          Load into Builder
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 10, marginBottom: 24 }}>
        {[...team.members].sort((a, b) => a.slot - b.slot).map((m) => {
          const pkmn = pokemonMap[m.pokemon_name]
          return (
            <div
              key={m.slot}
              style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '12px 8px', textAlign: 'center',
              }}
            >
              <div style={{
                width: 80, height: 80, borderRadius: '50%',
                background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                overflow: 'hidden', margin: '0 auto 8px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <img
                  src={spriteUrl(m.pokemon_name)}
                  alt={m.pokemon_name}
                  style={{ width: 68, height: 68, objectFit: 'contain' }}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              </div>
              <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 700, marginBottom: 4 }}>
                {titleCase(m.pokemon_name)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: 3, flexWrap: 'wrap', marginBottom: 4 }}>
                {(pkmn?.types ?? []).map((t) => (
                  <TypeBadge key={t.type_id} typeName={t.type_name} />
                ))}
              </div>
              {m.set_name && (
                <div style={{ fontSize: 9, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  {m.set_name}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <details style={{ marginBottom: 12 }}>
        <summary className="cursor-pointer select-none" style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
          ▶ Score Breakdown
        </summary>
        <div className="mt-3 pl-2">
          <BreakdownTable breakdown={team.breakdown} />
        </div>
      </details>

      <details>
        <summary className="cursor-pointer select-none" style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
          ▶ Team Analysis
        </summary>
        <div className="mt-3 pl-2">
          <AnalysisReport analysis={team.analysis} />
        </div>
      </details>
    </div>
  )
}
