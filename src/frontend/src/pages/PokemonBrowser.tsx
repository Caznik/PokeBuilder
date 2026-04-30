import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { PokemonList, PokemonDetail, CompetitiveSetResponse, CompetitiveSet, AbilityDetail, Pokemon } from '../api/types'
import TypeBadge from '../components/TypeBadge'

function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

function formatEvs(evs: CompetitiveSet['evs']): string {
  return Object.entries(evs)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => `${k.toUpperCase().replace('_', ' ')} ${v}`)
    .join(' / ') || '—'
}

function StatBar({ label, value }: { label: string; value: number }) {
  const pct = (value / 255) * 100
  const color =
    value >= 120 ? 'oklch(0.85 0.18 130)' :
    value >= 80  ? 'oklch(0.75 0.15 80)'  :
                   'oklch(0.60 0.12 25)'
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '36px 1fr 32px', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)' }}>
        {label}
      </span>
      <div style={{ height: 5, borderRadius: 3, background: 'oklch(0.22 0.005 250)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width 0.25s' }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'oklch(0.92 0.005 250)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </span>
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-dim)', marginBottom: 8 }}>
      {children}
    </div>
  )
}

export default function PokemonBrowser() {
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [data, setData] = useState<PokemonList | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<PokemonDetail | null>(null)
  const [selectedSets, setSelectedSets] = useState<CompetitiveSetResponse | null>(null)
  const [abilityDetails, setAbilityDetails] = useState<AbilityDetail[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<Pokemon[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const suppressSuggestions = useRef(false)

  useEffect(() => {
    if (!query) { setDebouncedQuery(''); setPage(1); return }
    const timer = setTimeout(() => { setDebouncedQuery(query); setPage(1) }, 400)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.pokemon.list(page, pageSize, debouncedQuery || undefined)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, pageSize, debouncedQuery])

  useEffect(() => {
    if (!query) { setSuggestions([]); setShowSuggestions(false); return }
    const timer = setTimeout(() => {
      api.pokemon.list(1, 8, query)
        .then((d) => {
          setSuggestions(d.items)
          if (!suppressSuggestions.current) setShowSuggestions(d.items.length > 0)
          suppressSuggestions.current = false
        })
        .catch(() => { suppressSuggestions.current = false })
    }, 150)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) setShowSuggestions(false)
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [])

  function handleSuggestionClick(name: string) {
    suppressSuggestions.current = true
    setQuery(name)
    setShowSuggestions(false)
    handleRowClick(name)
  }

  function handleRowClick(name: string) {
    setSelected(null)
    setSelectedSets(null)
    setAbilityDetails([])
    setDetailLoading(true)
    Promise.all([api.pokemon.getByName(name), api.competitiveSets.get(name)])
      .then(([detail, sets]) => {
        setSelected(detail)
        setSelectedSets(sets)
        Promise.all(
          detail.abilities.map((a) => api.abilities.getByName(a.ability_name).catch(() => null))
        ).then((results) => setAbilityDetails(results.filter((r): r is AbilityDetail => r !== null)))
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setDetailLoading(false))
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

  const inputStyle: React.CSSProperties = {
    background: 'var(--surface-2)',
    border: '1px solid var(--border-subtle)',
    color: 'var(--text)',
    borderRadius: 6,
    padding: '7px 12px',
    fontSize: 13,
    width: '100%',
    outline: 'none',
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Pokémon Browser</h1>

      {/* Search + page size */}
      <div className="flex gap-3 mb-4 items-center">
        <div className="relative flex-1" ref={searchRef}>
          <input
            type="text"
            placeholder="Search by name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true) }}
            style={{ ...inputStyle, width: '100%' }}
          />
          {showSuggestions && (
            <ul className="absolute z-10 w-full mt-1 rounded shadow-lg overflow-hidden" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
              {suggestions.map((p) => (
                <li
                  key={p.id}
                  onMouseDown={() => handleSuggestionClick(p.name)}
                  className="px-3 py-2 cursor-pointer flex items-center justify-between hover:bg-white/5 transition-colors"
                  style={{ fontSize: 13, color: 'var(--text)' }}
                >
                  <span>{titleCase(p.name)}</span>
                  <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>Gen {p.generation ?? '?'}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0" style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          <span>Show</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            style={{ ...inputStyle, width: 'auto', padding: '7px 28px 7px 10px', cursor: 'pointer' }}
          >
            {[10, 25, 50].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      {error && <p className="text-sm mb-3" style={{ color: 'oklch(0.65 0.18 25)' }}>{error}</p>}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg" style={{ border: '1px solid var(--border)' }}>
        <table className="w-full" style={{ fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
              {['Name', 'Gen', 'HP', 'Atk', 'Def', 'SpA', 'SpD', 'Spe'].map((h) => (
                <th key={h} className="pb-2 pt-2 pr-4 pl-3 text-left" style={{ fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={8} className="py-6 text-center" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>Loading...</td></tr>
            )}
            {!loading && data?.items.map((p) => (
              <tr
                key={p.id}
                onClick={() => handleRowClick(p.name)}
                className="cursor-pointer transition-colors hover:bg-white/[0.03]"
                style={{ borderBottom: '1px solid var(--border)' }}
              >
                <td className="py-2 pr-4 pl-3" style={{ color: 'oklch(0.70 0.13 240)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{titleCase(p.name)}</td>
                <td className="py-2 pr-4" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{p.generation ?? '—'}</td>
                {[p.base_hp, p.base_attack, p.base_defense, p.base_sp_attack, p.base_sp_defense, p.base_speed].map((v, i) => (
                  <td key={i} className="py-2 pr-4" style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontVariantNumeric: 'tabular-nums', color: 'oklch(0.85 0.005 250)' }}>{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && (
        <div className="flex items-center justify-between mt-3" style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <span>Showing {data.items.length} of {data.total}</span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 rounded disabled:opacity-40 transition-colors hover:bg-white/5"
              style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: 12 }}
            >
              ← Prev
            </button>
            <span className="px-2 py-1">{page} / {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 rounded disabled:opacity-40 transition-colors hover:bg-white/5"
              style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: 12 }}
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Detail panel */}
      {detailLoading && (
        <p className="mt-6" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>Loading details...</p>
      )}

      {selected && selectedSets && (
        <div className="mt-6 rounded-lg p-5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          {/* Name + types header */}
          <div className="flex items-center gap-3 mb-5">
            <h2 className="text-lg font-bold" style={{ fontFamily: 'var(--font-mono)' }}>{titleCase(selected.name)}</h2>
            <div className="flex gap-1.5">
              {selected.types.map((t) => <TypeBadge key={t.type_id} typeName={t.type_name} />)}
            </div>
          </div>

          {/* Sprite + stats */}
          <div className="flex gap-6 mb-6">
            <img
              src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${selected.id}.png`}
              alt={selected.name}
              className="w-36 h-36 object-contain shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
            <div className="flex-1">
              <SectionLabel>Base Stats</SectionLabel>
              <div className="space-y-2">
                <StatBar label="HP"  value={selected.base_hp} />
                <StatBar label="Atk" value={selected.base_attack} />
                <StatBar label="Def" value={selected.base_defense} />
                <StatBar label="SpA" value={selected.base_sp_attack} />
                <StatBar label="SpD" value={selected.base_sp_defense} />
                <StatBar label="Spe" value={selected.base_speed} />
              </div>
            </div>
          </div>

          {/* Abilities */}
          <div className="mb-6">
            <SectionLabel>Abilities</SectionLabel>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {selected.abilities.map((a) => {
                const detail = abilityDetails.find((d) => d.name === a.ability_name)
                return (
                  <div key={a.ability_id} className="rounded px-3 py-2" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
                    <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text)' }}>
                      {titleCase(a.ability_name)}
                      {a.is_hidden && <span style={{ marginLeft: 6, color: 'var(--text-dim)', fontWeight: 400 }}>(HA)</span>}
                    </p>
                    {detail?.description && (
                      <p className="mt-1 leading-relaxed" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {detail.description}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Competitive sets */}
          <div>
            <SectionLabel>Competitive Sets ({selectedSets.sets.length})</SectionLabel>
            {selectedSets.sets.length === 0 ? (
              <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>No competitive sets available.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {selectedSets.sets.map((set) => (
                  <div key={set.id} className="rounded p-3" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
                    <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
                      {set.name ?? `Set #${set.id}`}
                    </p>
                    <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>
                      {[
                        set.nature && `${titleCase(set.nature)}`,
                        set.ability && titleCase(set.ability),
                        set.item && set.item,
                      ].filter(Boolean).join(' · ')}
                    </p>
                    <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', marginBottom: 6 }}>
                      {formatEvs(set.evs)}
                    </p>
                    <ul className="space-y-0.5">
                      {set.moves.map((m, i) => (
                        <li key={i} style={{ fontSize: 11, color: 'oklch(0.80 0.005 250)' }}>· {titleCase(m)}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
