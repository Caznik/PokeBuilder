// src/frontend/src/components/PokemonDetailModal.tsx
import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { PokemonDetail, AbilityDetail, PokemonMove, CompetitiveSetResponse } from '../api/types'
import TypeBadge from './TypeBadge'

interface Props {
  pokemonName: string | null
  onClose: () => void
}

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function StatBar({ label, value }: { label: string; value: number }) {
  const pct = (value / 255) * 100
  const color =
    value >= 120 ? 'oklch(0.85 0.18 130)' :
    value >= 80  ? 'oklch(0.75 0.15 80)'  :
                   'oklch(0.60 0.12 25)'
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '32px 1fr 28px', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)' }}>
        {label}
      </span>
      <div style={{ height: 4, borderRadius: 2, background: 'oklch(0.22 0.005 250)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 2, transition: 'width 0.25s' }} />
      </div>
      <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'oklch(0.92 0.005 250)', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
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

export default function PokemonDetailModal({ pokemonName, onClose }: Props) {
  const [detail, setDetail]                 = useState<PokemonDetail | null>(null)
  const [abilityDetails, setAbilityDetails] = useState<AbilityDetail[]>([])
  const [sets, setSets]                     = useState<CompetitiveSetResponse | null>(null)
  const [moves, setMoves]                   = useState<PokemonMove[]>([])
  const [loading, setLoading]               = useState(false)
  const [error, setError]                   = useState<string | null>(null)

  useEffect(() => {
    if (!pokemonName) return
    let aborted = false
    setLoading(true)
    setError(null)
    setDetail(null)
    setSets(null)
    setMoves([])
    setAbilityDetails([])

    api.pokemon.getByName(pokemonName)
      .then(async (d) => {
        if (aborted) return
        setDetail(d)
        const [setsResult, movesResult, ...abilityResults] = await Promise.allSettled([
          api.competitiveSets.get(pokemonName),
          api.moves.forPokemon(d.id),
          ...d.abilities.map((a) => api.abilities.getByName(a.ability_name)),
        ])
        if (aborted) return
        if (setsResult.status === 'fulfilled') setSets(setsResult.value)
        if (movesResult.status === 'fulfilled') setMoves(movesResult.value.moves)
        setAbilityDetails(
          abilityResults
            .filter((r): r is PromiseFulfilledResult<AbilityDetail> => r.status === 'fulfilled')
            .map((r) => r.value)
        )
      })
      .catch((e: Error) => { if (!aborted) setError(e.message) })
      .finally(() => { if (!aborted) setLoading(false) })

    return () => { aborted = true }
  }, [pokemonName])

  const onCloseRef = useRef(onClose)
  useEffect(() => { onCloseRef.current = onClose })

  useEffect(() => {
    if (!pokemonName) return
    const onKeyDown = (e: KeyboardEvent) => { if (e.key === 'Escape') onCloseRef.current() }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [pokemonName])

  if (!pokemonName) return null

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 50, padding: 16,
      }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={pokemonName ? `${pokemonName.charAt(0).toUpperCase() + pokemonName.slice(1)} details` : 'Pokémon details'}
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          width: '100%', maxWidth: 640,
          maxHeight: '90vh', overflowY: 'auto',
          boxShadow: '0 20px 60px rgba(0,0,0,0.8)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '12px 12px 0' }}>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', fontSize: 18, cursor: 'pointer', padding: '4px 8px', borderRadius: 6, lineHeight: 1 }}
          >
            ✕
          </button>
        </div>
        {loading && (
          <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            Loading…
          </div>
        )}
        {error && (
          <div style={{ padding: 48, textAlign: 'center', color: 'oklch(0.65 0.18 25)', fontSize: 13 }}>
            {error}
          </div>
        )}
        {!loading && detail && (
          <>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' }}>
              <img
                src={`https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${detail.id}.png`}
                alt={detail.name}
                style={{ width: 80, height: 80, objectFit: 'contain', flexShrink: 0 }}
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
              />
              <div style={{ flex: 1 }}>
                <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text)', fontFamily: 'var(--font-mono)', margin: 0 }}>
                  {titleCase(detail.name)}
                </h2>
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  {detail.types.map((t) => <TypeBadge key={t.type_id} typeName={t.type_name} />)}
                </div>
              </div>
            </div>

            <div style={{ padding: '16px 20px' }}>
              {/* Base Stats */}
              <SectionLabel>Base Stats</SectionLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 20 }}>
                <StatBar label="HP"  value={detail.base_hp} />
                <StatBar label="Atk" value={detail.base_attack} />
                <StatBar label="Def" value={detail.base_defense} />
                <StatBar label="SpA" value={detail.base_sp_attack} />
                <StatBar label="SpD" value={detail.base_sp_defense} />
                <StatBar label="Spe" value={detail.base_speed} />
              </div>

              {/* Abilities */}
              <SectionLabel>Abilities</SectionLabel>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 20 }}>
                {detail.abilities.map((a) => {
                  const ad = abilityDetails.find((d) => d.name === a.ability_name)
                  return (
                    <div key={a.ability_id} style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '10px 12px' }}>
                      <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text)', margin: 0 }}>
                        {titleCase(a.ability_name)}
                        {a.is_hidden && <span style={{ marginLeft: 6, color: 'var(--text-dim)', fontWeight: 400 }}>(HA)</span>}
                      </p>
                      {ad?.description && (
                        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4, marginBottom: 0 }}>
                          {ad.description}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Learnable Moves */}
              <details style={{ marginBottom: 12 }}>
                <summary style={{
                  fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                  letterSpacing: '0.1em', color: 'var(--text-dim)', cursor: 'pointer',
                  userSelect: 'none', padding: '8px 0', borderTop: '1px solid var(--border)', listStyle: 'none',
                }}>
                  Learnable Moves ({moves.length})
                </summary>
                <div style={{ marginTop: 10, border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                    <thead>
                      <tr style={{ background: 'var(--surface-2)' }}>
                        {['Move', 'Type', 'Cat.', 'Pwr', 'PP'].map((h) => (
                          <th key={h} style={{
                            padding: '6px 10px',
                            textAlign: h === 'Move' ? 'left' : 'center',
                            fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                            letterSpacing: '0.08em', color: 'var(--text-dim)', fontWeight: 500,
                          }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {moves.map((m) => (
                        <tr key={m.id} style={{ borderTop: '1px solid var(--border)' }}>
                          <td style={{ padding: '5px 10px', color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                            {titleCase(m.name)}
                          </td>
                          <td style={{ padding: '5px 8px', textAlign: 'center' }}>
                            {m.type ? <TypeBadge typeName={m.type} /> : '—'}
                          </td>
                          <td style={{ padding: '5px 8px', textAlign: 'center', fontSize: 10, color: 'var(--text-muted)' }}>
                            {m.category ? titleCase(m.category) : '—'}
                          </td>
                          <td style={{ padding: '5px 8px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                            {m.power ?? '—'}
                          </td>
                          <td style={{ padding: '5px 8px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)' }}>
                            {m.pp ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>

              {/* Competitive Sets */}
              <details>
                <summary style={{
                  fontSize: 9, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                  letterSpacing: '0.1em', color: 'var(--text-dim)', cursor: 'pointer',
                  userSelect: 'none', padding: '8px 0', borderTop: '1px solid var(--border)', listStyle: 'none',
                }}>
                  Competitive Sets ({sets?.sets.length ?? 0})
                </summary>
                {sets && sets.sets.length > 0 ? (
                  <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    {sets.sets.map((set) => (
                      <div key={set.id} style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: '10px 12px' }}>
                        <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>
                          {set.name ?? `Set #${set.id}`}
                        </p>
                        <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>
                          {[
                            set.nature && titleCase(set.nature),
                            set.ability && titleCase(set.ability),
                            set.item,
                          ].filter(Boolean).join(' · ')}
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                          {set.moves.map((mv, i) => (
                            <li key={i} style={{ fontSize: 11, color: 'oklch(0.80 0.005 250)' }}>
                              · {titleCase(mv)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 8 }}>
                    No competitive sets available.
                  </p>
                )}
              </details>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
