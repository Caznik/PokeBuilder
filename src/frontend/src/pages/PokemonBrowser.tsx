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
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-8">{label}</span>
      <div className="flex-1 bg-gray-700 rounded h-1.5 overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded"
          style={{ width: `${(value / 180) * 100}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{value}</span>
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

  // Debounce query → debouncedQuery, reset to page 1 on change
  useEffect(() => {
    if (!query) {
      setDebouncedQuery('')
      setPage(1)
      return
    }
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [query])

  // Fetch list whenever page, pageSize, or debouncedQuery changes
  useEffect(() => {
    setLoading(true)
    setError(null)
    api.pokemon.list(page, pageSize, debouncedQuery || undefined)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, pageSize, debouncedQuery])

  // Suggestions — faster debounce, up to 8 matches
  useEffect(() => {
    if (!query) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }
    const timer = setTimeout(() => {
      api.pokemon.list(1, 8, query)
        .then((d) => {
          setSuggestions(d.items)
          if (!suppressSuggestions.current) {
            setShowSuggestions(d.items.length > 0)
          }
          suppressSuggestions.current = false
        })
        .catch(() => { suppressSuggestions.current = false })
    }, 150)
    return () => clearTimeout(timer)
  }, [query])

  // Close suggestions when clicking outside the search box
  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
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
          detail.abilities.map((a) =>
            api.abilities.getByName(a.ability_name).catch(() => null)
          )
        ).then((results) => {
          setAbilityDetails(results.filter((r): r is AbilityDetail => r !== null))
        })
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setDetailLoading(false))
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 1

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
            className="w-full bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          {showSuggestions && (
            <ul className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-600 rounded shadow-lg overflow-hidden">
              {suggestions.map((p) => (
                <li
                  key={p.id}
                  onMouseDown={() => handleSuggestionClick(p.name)}
                  className="px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 cursor-pointer flex items-center justify-between"
                >
                  <span>{titleCase(p.name)}</span>
                  <span className="text-xs text-gray-500">Gen {p.generation ?? '?'}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-400 shrink-0">
          <span>Show</span>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            className="bg-gray-800 border border-gray-600 rounded px-2 py-2 text-gray-200 focus:outline-none focus:border-blue-500"
          >
            {[10, 25, 50].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700 text-gray-400 text-left">
              {['Name', 'Gen', 'HP', 'Atk', 'Def', 'SpA', 'SpD', 'Spe'].map((h) => (
                <th key={h} className="pb-2 pr-4 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={8} className="py-4 text-gray-500 text-center">Loading...</td></tr>
            )}
            {!loading && data?.items.map((p) => (
              <tr
                key={p.id}
                onClick={() => handleRowClick(p.name)}
                className="border-b border-gray-800 hover:bg-gray-800 cursor-pointer"
              >
                <td className="py-2 pr-4 text-blue-300">{titleCase(p.name)}</td>
                <td className="py-2 pr-4 text-gray-400">{p.generation ?? '—'}</td>
                <td className="py-2 pr-4">{p.base_hp}</td>
                <td className="py-2 pr-4">{p.base_attack}</td>
                <td className="py-2 pr-4">{p.base_defense}</td>
                <td className="py-2 pr-4">{p.base_sp_attack}</td>
                <td className="py-2 pr-4">{p.base_sp_defense}</td>
                <td className="py-2 pr-4">{p.base_speed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && (
        <div className="flex items-center justify-between mt-3 text-sm text-gray-400">
          <span>Showing {data.items.length} of {data.total}</span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40 hover:bg-gray-700"
            >
              ← Prev
            </button>
            <span className="px-2 py-1">{page} / {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 bg-gray-800 rounded disabled:opacity-40 hover:bg-gray-700"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Detail panel */}
      {detailLoading && <p className="mt-6 text-gray-500 text-sm">Loading details...</p>}

      {selected && selectedSets && (
        <div className="mt-6 bg-gray-900 border border-gray-700 rounded-lg p-5">
          {/* Name + types header */}
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-lg font-bold">{titleCase(selected.name)}</h2>
            <div className="flex gap-1">
              {selected.types.map((t) => (
                <TypeBadge key={t.type_id} typeName={t.type_name} />
              ))}
            </div>
          </div>

          {/* Two-column: image | stats */}
          <div className="flex gap-6 mb-5">
            <img
              src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${selected.id}.png`}
              alt={selected.name}
              className="w-36 h-36 object-contain shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
            <div className="flex-1">
              <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Base Stats</p>
              <div className="space-y-2">
                <StatBar label="HP" value={selected.base_hp} />
                <StatBar label="Atk" value={selected.base_attack} />
                <StatBar label="Def" value={selected.base_defense} />
                <StatBar label="SpA" value={selected.base_sp_attack} />
                <StatBar label="SpD" value={selected.base_sp_defense} />
                <StatBar label="Spe" value={selected.base_speed} />
              </div>
            </div>
          </div>

          {/* Abilities — full width */}
          <div className="mb-5">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Abilities</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {selected.abilities.map((a) => {
                const detail = abilityDetails.find((d) => d.name === a.ability_name)
                return (
                  <div key={a.ability_id} className="bg-gray-800 rounded px-3 py-2">
                    <p className="text-xs font-medium">
                      {titleCase(a.ability_name)}
                      {a.is_hidden && <span className="ml-1 text-gray-500">(HA)</span>}
                    </p>
                    {detail?.description && (
                      <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                        {detail.description}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Competitive sets — full width */}
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">
              Competitive Sets ({selectedSets.sets.length})
            </p>
            {selectedSets.sets.length === 0 ? (
              <p className="text-gray-500 text-sm">No competitive sets available for this Pokémon.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {selectedSets.sets.map((set) => (
                  <div key={set.id} className="bg-gray-800 rounded p-3">
                    <p className="font-medium text-sm mb-1">{set.name ?? `Set #${set.id}`}</p>
                    <p className="text-xs text-gray-400">
                      {[
                        set.nature && `Nature: ${set.nature}`,
                        set.ability && `Ability: ${set.ability}`,
                        set.item && `Item: ${set.item}`,
                      ].filter(Boolean).join(' · ')}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">EVs: {formatEvs(set.evs)}</p>
                    <ul className="mt-2 space-y-0.5">
                      {set.moves.map((m, i) => (
                        <li key={i} className="text-xs text-gray-300">• {titleCase(m)}</li>
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
