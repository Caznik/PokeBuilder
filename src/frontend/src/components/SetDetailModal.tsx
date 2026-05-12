import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import type { GenerationMember, PokemonDetail, CompetitiveSet } from '../api/types'
import TypeBadge from './TypeBadge'

// ── Constants ─────────────────────────────────────────────────────────────────

const STAT_KEYS = ['hp', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed'] as const
const STAT_LABELS: Record<string, string> = {
  hp: 'HP', attack: 'Atk', defense: 'Def',
  sp_attack: 'SpA', sp_defense: 'SpD', speed: 'Spe',
}

const NATURE_MODS: Record<string, { plus: string; minus: string }> = {
  hardy:   { plus: '',           minus: '' },
  lonely:  { plus: 'attack',     minus: 'defense' },
  brave:   { plus: 'attack',     minus: 'speed' },
  adamant: { plus: 'attack',     minus: 'sp_attack' },
  naughty: { plus: 'attack',     minus: 'sp_defense' },
  bold:    { plus: 'defense',    minus: 'attack' },
  docile:  { plus: '',           minus: '' },
  relaxed: { plus: 'defense',    minus: 'speed' },
  impish:  { plus: 'defense',    minus: 'sp_attack' },
  lax:     { plus: 'defense',    minus: 'sp_defense' },
  timid:   { plus: 'speed',      minus: 'attack' },
  hasty:   { plus: 'speed',      minus: 'defense' },
  serious: { plus: '',           minus: '' },
  jolly:   { plus: 'speed',      minus: 'sp_attack' },
  naive:   { plus: 'speed',      minus: 'sp_defense' },
  modest:  { plus: 'sp_attack',  minus: 'attack' },
  mild:    { plus: 'sp_attack',  minus: 'defense' },
  quiet:   { plus: 'sp_attack',  minus: 'speed' },
  bashful: { plus: '',           minus: '' },
  rash:    { plus: 'sp_attack',  minus: 'sp_defense' },
  calm:    { plus: 'sp_defense', minus: 'attack' },
  gentle:  { plus: 'sp_defense', minus: 'defense' },
  sassy:   { plus: 'sp_defense', minus: 'speed' },
  careful: { plus: 'sp_defense', minus: 'sp_attack' },
  quirky:  { plus: '',           minus: '' },
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function calcStat(base: number, ev: number, isHp: boolean, natureMod: number): number {
  const iv = 31, level = 50
  if (isHp) return Math.floor((2 * base + iv + Math.floor(ev / 4)) * level / 100) + level + 10
  return Math.floor((Math.floor((2 * base + iv + Math.floor(ev / 4)) * level / 100) + 5) * natureMod)
}

function spriteUrl(name: string) {
  return `https://img.pokemondb.net/sprites/home/normal/${name}.png`
}

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// ── Component ─────────────────────────────────────────────────────────────────

export interface SetDetailModalProps {
  member: GenerationMember
  onClose: () => void
}

export default function SetDetailModal({ member, onClose }: SetDetailModalProps) {
  const [pokemon, setPokemon] = useState<PokemonDetail | null>(null)
  const [set, setSet] = useState<CompetitiveSet | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      api.pokemon.getByName(member.pokemon_name),
      api.competitiveSets.get(member.pokemon_name),
    ]).then(([pokemonData, setData]) => {
      if (cancelled) return
      const matched = setData.sets.find((s) => s.id === member.set_id) ?? null
      setPokemon(pokemonData)
      setSet(matched)
      setLoading(false)
    }).catch(() => {
      if (!cancelled) {
        setError('Could not load set details.')
        setLoading(false)
      }
    })
    return () => { cancelled = true }
  }, [member.pokemon_name, member.set_id])

  const backdropRef = useRef<HTMLDivElement>(null)
  useEffect(() => { backdropRef.current?.focus() }, [])

  const handleKeyDown = useCallback((e: { key: string }) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  const natureMods = NATURE_MODS[(member.nature ?? '').toLowerCase()] ?? { plus: '', minus: '' }

  function natureMod(statKey: string): number {
    if (natureMods.plus === statKey) return 1.1
    if (natureMods.minus === statKey) return 0.9
    return 1.0
  }

  function baseForStat(key: string): number {
    if (!pokemon) return 0
    const map: Record<string, number> = {
      hp: pokemon.base_hp, attack: pokemon.base_attack, defense: pokemon.base_defense,
      sp_attack: pokemon.base_sp_attack, sp_defense: pokemon.base_sp_defense, speed: pokemon.base_speed,
    }
    return map[key] ?? 0
  }

  const computedStats = pokemon && set
    ? Object.fromEntries(
        STAT_KEYS.map((key) => {
          const ev = set.evs[key as keyof typeof set.evs] ?? 0
          const mod = key === 'hp' ? 1 : natureMod(key)
          return [key, calcStat(baseForStat(key), ev, key === 'hp', mod)]
        })
      )
    : null

  const maxStat = computedStats ? Math.max(...Object.values(computedStats)) : 1
  const totalEvs = set ? Object.values(set.evs).reduce((a, b) => a + b, 0) : 0

  return (
    <div
      ref={backdropRef}
      data-testid="modal-backdrop"
      tabIndex={-1}
      onKeyDown={handleKeyDown}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'oklch(0.05 0.005 250 / 0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        outline: 'none',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          width: 640, maxHeight: '85vh', display: 'flex', flexDirection: 'column',
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 10, overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Hero */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 14, padding: '14px 18px',
          background: 'var(--surface-2)', borderBottom: '1px solid var(--border)',
        }}>
          <div style={{
            width: 64, height: 64, borderRadius: '50%', flexShrink: 0,
            background: 'var(--surface)', border: '1px solid var(--border-subtle)',
            overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <img
              src={spriteUrl(member.pokemon_name)}
              alt={member.pokemon_name}
              style={{ width: 52, height: 52, objectFit: 'contain' }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 16, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
              {titleCase(member.pokemon_name)}
            </div>
            {pokemon && (
              <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                {pokemon.types.map((t) => <TypeBadge key={t.type_id} typeName={t.type_name} />)}
              </div>
            )}
            <div style={{ marginTop: 5, display: 'flex', gap: 12, fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              {member.nature && (
                <span>Nature: <span style={{ color: 'var(--text)' }}>{titleCase(member.nature)}</span></span>
              )}
              {member.ability && (
                <span>Ability: <span style={{ color: 'var(--text)' }}>{titleCase(member.ability)}</span></span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: 18, cursor: 'pointer', alignSelf: 'flex-start', lineHeight: 1 }}
          >
            ✕
          </button>
        </div>

        {/* Body */}
        {loading && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, fontSize: 13, color: 'var(--text-muted)' }}>
            Loading…
          </div>
        )}
        {error && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, fontSize: 13, color: 'oklch(0.60 0.18 25)' }}>
            {error}
          </div>
        )}
        {!loading && !error && set && computedStats && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', flex: 1, overflow: 'hidden' }}>

            {/* Left: moves + item + set name */}
            <div style={{ padding: '14px 16px', borderRight: '1px solid var(--border)', overflowY: 'auto' }}>
              <div style={sectionLabel}>Moves</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 14 }}>
                {set.moves.map((move, i) => (
                  <div key={i} style={{
                    background: 'var(--surface-2)', borderRadius: 4,
                    padding: '6px 10px', fontSize: 10, color: 'var(--text)',
                    display: 'flex', alignItems: 'center', gap: 7,
                  }}>
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: 'var(--border)', flexShrink: 0, display: 'inline-block',
                    }} />
                    {move}
                  </div>
                ))}
                {set.moves.length === 0 && (
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontStyle: 'italic' }}>No moves recorded</div>
                )}
              </div>

              {set.item && (
                <>
                  <div style={sectionLabel}>Item</div>
                  <div style={{
                    background: 'var(--surface-2)', borderRadius: 4,
                    padding: '6px 10px', fontSize: 10, color: 'var(--text)', marginBottom: 14,
                  }}>
                    {set.item}
                  </div>
                </>
              )}

              {set.name && (
                <>
                  <div style={sectionLabel}>Set Name</div>
                  <div style={{ fontSize: 9, color: 'var(--text-muted)', fontStyle: 'italic' }}>{set.name}</div>
                </>
              )}
            </div>

            {/* Right: stat bars */}
            <div style={{ padding: '14px 16px', overflowY: 'auto' }}>
              <div style={sectionLabel}>Stats — Lv 50 / 31 IVs</div>
              {STAT_KEYS.map((key) => {
                const ev = set.evs[key as keyof typeof set.evs] ?? 0
                const val = computedStats[key]
                const pct = maxStat > 0 ? (val / maxStat) * 100 : 0
                const isPlus = natureMods.plus === key
                const isMinus = natureMods.minus === key
                const labelColor = isPlus ? 'var(--accent)' : isMinus ? 'oklch(0.60 0.18 25)' : 'var(--text-muted)'
                const barColor = isPlus ? 'oklch(0.75 0.14 145)' : isMinus ? 'oklch(0.60 0.18 25)' : 'var(--accent)'
                const valColor = isPlus ? 'oklch(0.75 0.14 145)' : isMinus ? 'oklch(0.60 0.18 25)' : 'var(--text)'
                return (
                  <div key={key} style={{ display: 'grid', gridTemplateColumns: '30px 1fr 30px 36px', alignItems: 'center', gap: 5, marginBottom: 7 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: labelColor, textTransform: 'uppercase' }}>
                      {STAT_LABELS[key]}{isPlus ? '+' : isMinus ? '−' : ''}
                    </span>
                    <div style={{ background: 'var(--surface-2)', borderRadius: 2, height: 5, overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: barColor, borderRadius: 2, transition: 'width 0.15s' }} />
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', textAlign: 'right' }}>{ev}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, textAlign: 'right', color: valColor }}>{val}</span>
                  </div>
                )
              })}

              {/* EV total */}
              <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3, fontSize: 8, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  <span>EV Total</span>
                  <span>{totalEvs} / 508</span>
                </div>
                <div style={{ height: 3, background: 'var(--surface-2)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(100, (totalEvs / 508) * 100)}%`, height: '100%', background: 'var(--accent)', borderRadius: 2 }} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'flex-end', padding: '10px 18px',
          borderTop: '1px solid var(--border)', background: 'var(--surface-2)',
        }}>
          <button
            onClick={onClose}
            style={{
              fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
              letterSpacing: '0.06em', background: 'none',
              border: '1px solid var(--border)', color: 'var(--text-muted)',
              borderRadius: 4, padding: '6px 18px', cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Shared style ──────────────────────────────────────────────────────────────

const sectionLabel = {
  fontSize: 8, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' as const,
  letterSpacing: '0.12em', color: 'var(--text-muted)', marginBottom: 8,
}
