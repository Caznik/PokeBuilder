import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Regulation, RegulationDetail } from '../api/types'
import PokemonDetailModal from '../components/PokemonDetailModal'

function spriteUrl(name: string) {
  return `https://img.pokemondb.net/sprites/home/normal/${name}.png`
}

export default function Regulations() {
  const [regulations, setRegulations] = useState<Regulation[]>([])
  const [selected, setSelected] = useState<RegulationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedPokemon, setSelectedPokemon] = useState<string | null>(null)

  useEffect(() => {
    api.regulations.list()
      .then((list) => {
        setRegulations(list)
        if (list.length > 0) fetchDetail(list[0].id)
      })
      .catch(() => setError('Failed to load regulations'))
      .finally(() => setLoading(false))
  }, [])

  function fetchDetail(id: number) {
    setSelectedPokemon(null)
    setDetailLoading(true)
    api.regulations.get(id)
      .then(setSelected)
      .catch(() => setError('Failed to load regulation details'))
      .finally(() => setDetailLoading(false))
  }

  if (loading) {
    return <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading regulations…</p>
  }

  if (error) {
    return <p className="text-sm text-red-400">{error}</p>
  }

  if (regulations.length === 0) {
    return (
      <div>
        <h1 className="text-xl font-bold mb-4">Regulations</h1>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No regulations found.</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">Regulations</h1>

      <div className="flex gap-4 items-start">
        {/* Sidebar: regulation list */}
        <div className="w-48 shrink-0 space-y-1">
          {regulations.map((r) => (
            <button
              key={r.id}
              onClick={() => fetchDetail(r.id)}
              className="w-full text-left text-sm px-3 py-2 rounded transition-colors"
              style={{
                background: selected?.id === r.id ? 'var(--surface-2)' : 'transparent',
                color: selected?.id === r.id ? 'var(--accent)' : 'var(--text-muted)',
                border: selected?.id === r.id ? '1px solid var(--border)' : '1px solid transparent',
                fontWeight: selected?.id === r.id ? 600 : 400,
              }}
            >
              {r.name}
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div
          className="flex-1 rounded-lg p-4"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          {detailLoading && (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading…</p>
          )}

          {!detailLoading && selected && (
            <>
              <div className="mb-4">
                <h2 className="text-lg font-semibold" style={{ color: 'var(--text)' }}>{selected.name}</h2>
                {selected.description && (
                  <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>{selected.description}</p>
                )}
                <p className="text-xs mt-2" style={{ color: 'var(--text-dim)' }}>
                  {selected.pokemon.length} Pokémon allowed
                </p>
              </div>

              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3">
                {selected.pokemon.map((name) => (
                  <div
                    key={name}
                    className="flex flex-col items-center gap-1 rounded-lg p-2 cursor-pointer transition-colors hover:bg-white/10"
                    style={{ background: 'var(--surface-2)' }}
                    onClick={() => setSelectedPokemon(name)}
                  >
                    <img
                      src={spriteUrl(name)}
                      alt={name}
                      className="w-12 h-12 object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                    />
                    <span
                      className="text-xs text-center capitalize leading-tight"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {name}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <PokemonDetailModal
        pokemonName={selectedPokemon}
        onClose={() => setSelectedPokemon(null)}
      />
    </div>
  )
}
