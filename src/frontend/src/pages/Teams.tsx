import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Regulation, SavedTeamSummary, PokemonType } from '../api/types'
import TypeBadge from '../components/TypeBadge'
import TeamBuilder from './TeamBuilder'

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function spriteUrl(name: string) {
  return `https://img.pokemondb.net/sprites/home/normal/${name}.png`
}

// undefined = all teams; null = no regulation; number = specific regulation
type RegulationFilter = number | null | undefined

export default function Teams() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') ?? 'build') as 'build' | 'saved'
  const navigate = useNavigate()

  const [teams, setTeams] = useState<SavedTeamSummary[]>([])
  const [teamsLoaded, setTeamsLoaded] = useState(false)
  const [teamsLoading, setTeamsLoading] = useState(false)
  const [teamsError, setTeamsError] = useState<string | null>(null)
  const [typesMap, setTypesMap] = useState<Record<string, PokemonType[]>>({})
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const [regulations, setRegulations] = useState<Regulation[]>([])
  const [regulationFilter, setRegulationFilter] = useState<RegulationFilter>(undefined)

  // Fetch regulations list once when the saved tab is first visited
  useEffect(() => {
    if (tab !== 'saved') return
    api.regulations.list().then(setRegulations).catch(() => {/* non-critical */})
  }, [tab])

  // Fetch teams when the tab is active or when the regulation filter changes
  useEffect(() => {
    if (tab !== 'saved' && teamsLoaded) return
    setTeamsLoading(true)
    setTeamsError(null)
    api.savedTeams.list(regulationFilter)
      .then((list) => {
        setTeams(list)
        setTeamsLoaded(true)
        if (tab !== 'saved' || list.length === 0) return
        const uniqueNames = [...new Set(list.flatMap((t) => t.members.map((m) => m.pokemon_name)))]
        Promise.allSettled(
          uniqueNames.map((name) => api.pokemon.getByName(name).then((p) => ({ name: p.name, types: p.types })))
        ).then((results) => {
          const map: Record<string, PokemonType[]> = {}
          results.forEach((r) => {
            if (r.status === 'fulfilled') map[r.value.name] = r.value.types
          })
          setTypesMap(map)
        })
      })
      .catch((e: unknown) => setTeamsError(e instanceof Error ? e.message : 'Failed to load teams'))
      .finally(() => setTeamsLoading(false))
  }, [tab, regulationFilter])

  function switchTab(t: 'build' | 'saved') {
    if (t === 'build') setSearchParams({})
    else setSearchParams({ tab: 'saved' })
  }

  function handleFilterChange(value: string) {
    if (value === 'all') setRegulationFilter(undefined)
    else if (value === 'none') setRegulationFilter(null)
    else setRegulationFilter(Number(value))
    setTeamsLoaded(false)
  }

  async function handleDelete(id: number) {
    setDeleteError(null)
    try {
      await api.savedTeams.delete(id)
      setTeams((prev) => prev.filter((t) => t.id !== id))
    } catch (e: unknown) {
      setDeleteError(e instanceof Error ? e.message : 'Failed to delete')
    } finally {
      setConfirmDelete(null)
    }
  }

  const filterActive = regulationFilter !== undefined

  return (
    <div>
      {/* Tab toggle */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24 }}>
        {(['build', 'saved'] as const).map((t) => {
          const label = t === 'build'
            ? 'Build'
            : `My Teams${teamsLoaded ? ` (${teams.length})` : ''}`
          const active = tab === t
          return (
            <button
              key={t}
              onClick={() => switchTab(t)}
              style={{
                fontSize: 12, fontFamily: 'var(--font-mono)', padding: '5px 16px',
                borderRadius: 999, border: 'none', cursor: 'pointer',
                background: active ? 'var(--accent)' : 'var(--surface-2)',
                color: active ? 'var(--accent-fg)' : 'var(--text-muted)',
                fontWeight: active ? 600 : 400,
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Build tab — always mounted to preserve builder state */}
      <div style={{ display: tab === 'build' ? 'block' : 'none' }}>
        <TeamBuilder />
      </div>

      {/* My Teams tab */}
      {tab === 'saved' && (
        <div className="space-y-4">
          {/* Regulation filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <label
              htmlFor="regulation-filter"
              style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}
            >
              Regulation
            </label>
            <select
              id="regulation-filter"
              value={
                regulationFilter === undefined ? 'all'
                : regulationFilter === null ? 'none'
                : String(regulationFilter)
              }
              onChange={(e) => handleFilterChange(e.target.value)}
              style={{
                fontSize: 11, fontFamily: 'var(--font-mono)',
                background: 'var(--surface-2)', color: 'var(--text)',
                border: '1px solid var(--border)', borderRadius: 6,
                padding: '3px 8px', cursor: 'pointer',
              }}
            >
              <option value="all">All</option>
              <option value="none">No regulation</option>
              {regulations.map((r) => (
                <option key={r.id} value={String(r.id)}>{r.name}</option>
              ))}
            </select>
          </div>

          {teamsLoading && (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading...</p>
          )}
          {teamsError && (
            <p style={{ color: 'oklch(0.55 0.18 25)', fontSize: 13 }}>{teamsError}</p>
          )}
          {deleteError && (
            <p style={{ color: 'oklch(0.55 0.18 25)', fontSize: 12 }}>{deleteError}</p>
          )}
          {!teamsLoading && teamsLoaded && teams.length === 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              {filterActive
                ? 'No saved teams match this filter.'
                : 'No saved teams yet. Build and score a team, then save it.'}
            </p>
          )}
          {teams.map((team) => (
            <div
              key={team.id}
              className="rounded-lg"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              {/* Card header */}
              <div
                className="flex items-start gap-3 p-4 cursor-pointer"
                onClick={() => navigate(`/teams/${team.id}`)}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 14, marginBottom: 2 }}>
                    {team.name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {new Date(team.created_at).toLocaleDateString()} · {team.members.length} Pokémon
                  </div>
                </div>
                {confirmDelete === team.id ? (
                  <span className="flex items-center gap-1">
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Delete?</span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(team.id) }}
                      style={{ fontSize: 10, color: 'oklch(0.55 0.18 25)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}
                    >Yes</button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setConfirmDelete(null) }}
                      style={{ fontSize: 10, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}
                    >No</button>
                  </span>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); setConfirmDelete(team.id) }}
                    style={{ fontSize: 16, lineHeight: 1, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                    title="Delete team"
                  >
                    🗑
                  </button>
                )}
              </div>

              {/* Pokémon cards */}
              <div
                style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8, padding: '0 16px 16px', cursor: 'pointer' }}
                onClick={() => navigate(`/teams/${team.id}`)}
              >
                {[...team.members].sort((a, b) => a.slot - b.slot).map((m) => (
                  <div key={m.slot} style={{ textAlign: 'center' }}>
                    <div style={{
                      width: 68, height: 68, borderRadius: '50%',
                      background: 'var(--surface-2)', border: '1px solid var(--border-subtle)',
                      overflow: 'hidden', margin: '0 auto 6px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <img
                        src={spriteUrl(m.pokemon_name)}
                        alt={m.pokemon_name}
                        style={{ width: 58, height: 58, objectFit: 'contain' }}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                      />
                    </div>
                    <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 600, marginBottom: 3 }}>
                      {titleCase(m.pokemon_name)}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                      {(typesMap[m.pokemon_name] ?? []).map((t) => (
                        <TypeBadge key={t.type_id} typeName={t.type_name} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
