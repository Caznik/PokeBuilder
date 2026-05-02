import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api/client'
import type { SavedTeamMember, SavedTeamDetail, PokemonDetail, PokemonMove } from '../api/types'
import TypeBadge from './TypeBadge'

// ── Constants ────────────────────────────────────────────────────────────────

const NATURES = [
  'hardy','lonely','brave','adamant','naughty',
  'bold','docile','relaxed','impish','lax',
  'timid','hasty','serious','jolly','naive',
  'modest','mild','quiet','bashful','rash',
  'calm','gentle','sassy','careful','quirky',
]

const NATURE_MODS: Record<string, { plus: string; minus: string }> = {
  hardy:   { plus: '',           minus: '' },     lonely:  { plus: 'attack',     minus: 'defense' },
  brave:   { plus: 'attack',     minus: 'speed' }, adamant: { plus: 'attack',     minus: 'sp_attack' },
  naughty: { plus: 'attack',     minus: 'sp_defense' }, bold: { plus: 'defense',    minus: 'attack' },
  docile:  { plus: '',           minus: '' },     relaxed: { plus: 'defense',    minus: 'speed' },
  impish:  { plus: 'defense',    minus: 'sp_attack' }, lax: { plus: 'defense',    minus: 'sp_defense' },
  timid:   { plus: 'speed',      minus: 'attack' }, hasty: { plus: 'speed',      minus: 'defense' },
  serious: { plus: '',           minus: '' },     jolly:   { plus: 'speed',      minus: 'sp_attack' },
  naive:   { plus: 'speed',      minus: 'sp_defense' }, modest: { plus: 'sp_attack',  minus: 'attack' },
  mild:    { plus: 'sp_attack',  minus: 'defense' }, quiet: { plus: 'sp_attack',  minus: 'speed' },
  bashful: { plus: '',           minus: '' },     rash:    { plus: 'sp_attack',  minus: 'sp_defense' },
  calm:    { plus: 'sp_defense', minus: 'attack' }, gentle: { plus: 'sp_defense', minus: 'defense' },
  sassy:   { plus: 'sp_defense', minus: 'speed' }, careful: { plus: 'sp_defense', minus: 'sp_attack' },
  quirky:  { plus: '',           minus: '' },
}

const TERA_TYPES = [
  'normal','fire','water','electric','grass','ice',
  'fighting','poison','ground','flying','psychic','bug',
  'rock','ghost','dragon','dark','steel','fairy',
]

const EV_PRESETS: Record<string, Record<string, number>> = {
  'Bulky':      { hp: 252, attack: 0,   defense: 252, sp_attack: 0,   sp_defense: 4,   speed: 0   },
  'Phys Sweep': { hp: 4,   attack: 252, defense: 0,   sp_attack: 0,   sp_defense: 0,   speed: 252 },
  'Spec Sweep': { hp: 4,   attack: 0,   defense: 0,   sp_attack: 252, sp_defense: 0,   speed: 252 },
  'Reset':      { hp: 0,   attack: 0,   defense: 0,   sp_attack: 0,   sp_defense: 0,   speed: 0   },
}

const STAT_KEYS = ['hp','attack','defense','sp_attack','sp_defense','speed'] as const
const STAT_LABELS: Record<string, string> = {
  hp: 'HP', attack: 'Atk', defense: 'Def',
  sp_attack: 'SpA', sp_defense: 'SpD', speed: 'Spe',
}

// bg values taken directly from TypeBadge.tsx for visual consistency
const TYPE_COLOR: Record<string, string> = {
  normal:'oklch(0.55 0.02 80)',   fire:'oklch(0.55 0.16 35)',
  water:'oklch(0.55 0.13 240)',   electric:'oklch(0.65 0.16 95)',
  grass:'oklch(0.55 0.13 145)',   ice:'oklch(0.70 0.10 200)',
  fighting:'oklch(0.50 0.15 25)', poison:'oklch(0.50 0.14 320)',
  ground:'oklch(0.55 0.10 65)',   flying:'oklch(0.65 0.08 260)',
  psychic:'oklch(0.60 0.14 350)', bug:'oklch(0.60 0.13 120)',
  rock:'oklch(0.50 0.07 70)',     ghost:'oklch(0.45 0.10 290)',
  dragon:'oklch(0.50 0.16 270)',  dark:'oklch(0.35 0.04 30)',
  steel:'oklch(0.60 0.03 230)',   fairy:'oklch(0.75 0.10 350)',
}

// ── Helpers ──────────────────────────────────────────────────────────────────

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

function evTotal(evs: Record<string, number>): number {
  return Object.values(evs).reduce((a, b) => a + b, 0)
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Draft {
  item: string
  ability: string
  nature: string
  tera_type: string
  moves: [string, string, string, string]
  evs: { hp: number; attack: number; defense: number; sp_attack: number; sp_defense: number; speed: number }
}

interface Props {
  teamId: number
  member: SavedTeamMember
  pokemon: PokemonDetail
  onClose: () => void
  onSaved: (updated: SavedTeamDetail) => void
}

export default function MemberDetailModal({ teamId, member, pokemon, onClose, onSaved }: Props) {
  const [draft, setDraft] = useState<Draft>({
    item: member.item ?? '',
    ability: member.ability ?? '',
    nature: member.nature ?? '',
    tera_type: member.tera_type ?? '',
    moves: [
      member.moves?.[0] ?? '',
      member.moves?.[1] ?? '',
      member.moves?.[2] ?? '',
      member.moves?.[3] ?? '',
    ],
    evs: member.evs
      ? { hp: member.evs.hp ?? 0, attack: member.evs.attack ?? 0, defense: member.evs.defense ?? 0,
          sp_attack: member.evs.sp_attack ?? 0, sp_defense: member.evs.sp_defense ?? 0, speed: member.evs.speed ?? 0 }
      : { hp: 0, attack: 0, defense: 0, sp_attack: 0, sp_defense: 0, speed: 0 },
  })

  const [allMoves, setAllMoves] = useState<PokemonMove[]>([])
  const [pickingSlot, setPickingSlot] = useState<0 | 1 | 2 | 3 | null>(null)
  const [moveSearch, setMoveSearch] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const modalRef = useRef<HTMLDivElement>(null)

  // Load learnable moves
  useEffect(() => {
    api.moves.forPokemon(pokemon.id).then((r) => setAllMoves(r.moves)).catch(() => {})
  }, [pokemon.id])

  // Escape closes or exits picker
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (pickingSlot !== null) { setPickingSlot(null); setMoveSearch('') }
      else onClose()
    }
  }, [pickingSlot, onClose])

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  // Focus trap
  useEffect(() => {
    const el = modalRef.current
    if (!el) return
    const focusable = el.querySelectorAll<HTMLElement>(
      'button, input, select, [tabindex]:not([tabindex="-1"])'
    )
    if (focusable.length) focusable[0].focus()
  }, [])

  const natureMods = NATURE_MODS[draft.nature.toLowerCase()] ?? { plus: '', minus: '' }

  function natureMod(statKey: string): number {
    if (natureMods.plus === statKey) return 1.1
    if (natureMods.minus === statKey) return 0.9
    return 1.0
  }

  function baseForStat(key: string): number {
    const map: Record<string, number> = {
      hp: pokemon.base_hp, attack: pokemon.base_attack, defense: pokemon.base_defense,
      sp_attack: pokemon.base_sp_attack, sp_defense: pokemon.base_sp_defense, speed: pokemon.base_speed,
    }
    return map[key] ?? 0
  }

  function setEv(key: string, raw: number) {
    setDraft((d) => {
      const remaining = 508 - evTotal(d.evs) + (d.evs[key as keyof typeof d.evs] ?? 0)
      const value = Math.max(0, Math.min(252, Math.min(remaining, isNaN(raw) ? 0 : raw)))
      return { ...d, evs: { ...d.evs, [key]: value } }
    })
  }

  const filteredMoves = allMoves.filter((m) =>
    m.name.toLowerCase().includes(moveSearch.toLowerCase())
  )

  function pickMove(moveName: string) {
    if (pickingSlot === null) return
    const newMoves = [...draft.moves] as [string, string, string, string]
    newMoves[pickingSlot] = moveName
    setDraft((d) => ({ ...d, moves: newMoves }))
    setPickingSlot(null)
    setMoveSearch('')
  }

  async function handleSave() {
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await api.savedTeams.updateMember(teamId, member.slot, {
        pokemon_name: member.pokemon_name,
        set_id: member.set_id,
        item: draft.item || null,
        tera_type: draft.tera_type || null,
        evs: draft.evs,
        moves: draft.moves,
        nature: draft.nature || null,
        ability: draft.ability || null,
      })
      onSaved(updated)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Save failed')
      setSaving(false)
    }
  }

  const total = evTotal(draft.evs)

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'oklch(0.05 0.005 250 / 0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        ref={modalRef}
        style={{
          width: 720, maxHeight: '88vh', display: 'flex', flexDirection: 'column',
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 10, overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Hero */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 16, padding: '16px 20px',
          background: 'var(--surface-2)', borderBottom: '1px solid var(--border)',
        }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: 'var(--surface)', border: '1px solid var(--border-subtle)',
            overflow: 'hidden', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <img
              src={spriteUrl(member.pokemon_name)}
              alt={member.pokemon_name}
              style={{ width: 60, height: 60, objectFit: 'contain' }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 18, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
              {titleCase(member.pokemon_name)}
            </div>
            <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
              {pokemon.types.map((t) => <TypeBadge key={t.type_id} typeName={t.type_name} />)}
            </div>
            {member.set_name && (
              <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                {member.set_name}
              </div>
            )}
          </div>
        </div>

        {/* Body */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', flex: 1, overflow: 'hidden' }}>

          {/* Left column */}
          <div style={{ borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {pickingSlot !== null ? (
              /* Picker view */
              <>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
                  borderBottom: '1px solid var(--border)',
                  background: 'oklch(0.14 0.005 250)',
                }}>
                  <button
                    onClick={() => { setPickingSlot(null); setMoveSearch('') }}
                    style={{
                      fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--accent)',
                      background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                    }}
                  >
                    ← Back
                  </button>
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                    Pick a move · Slot {pickingSlot + 1}
                  </span>
                </div>
                <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                  <input
                    autoFocus
                    type="text"
                    placeholder="Search moves…"
                    value={moveSearch}
                    onChange={(e) => setMoveSearch(e.target.value)}
                    style={{
                      width: '100%', background: 'var(--surface-2)',
                      border: '1px solid var(--border)', borderRadius: 3,
                      padding: '4px 8px', fontFamily: 'var(--font-mono)',
                      fontSize: 10, color: 'var(--text)', outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div style={{ overflowY: 'auto', flex: 1 }}>
                  {filteredMoves.map((m) => {
                    const color = TYPE_COLOR[m.type ?? ''] ?? 'var(--text-muted)'
                    const isSelected = draft.moves[pickingSlot] === m.name
                    return (
                      <div
                        key={m.id}
                        onClick={() => pickMove(m.name)}
                        style={{
                          display: 'grid', gridTemplateColumns: '8px 1fr auto auto',
                          alignItems: 'center', gap: 8, padding: '6px 12px',
                          cursor: 'pointer',
                          background: isSelected ? 'oklch(0.85 0.18 130 / 0.10)' : 'transparent',
                        }}
                        onMouseEnter={(e) => { if (!isSelected) (e.currentTarget as HTMLDivElement).style.background = 'var(--surface-2)' }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.background = isSelected ? 'oklch(0.85 0.18 130 / 0.10)' : 'transparent' }}
                      >
                        <div style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
                        <span style={{ fontSize: 10, fontWeight: 500 }}>{m.name}</span>
                        <span style={{
                          fontSize: 7, padding: '2px 6px', borderRadius: 999,
                          textTransform: 'uppercase', fontFamily: 'var(--font-mono)',
                          background: color.replace(')', ' / 0.15)'), color,
                          border: `1px solid ${color.replace(')', ' / 0.3)')}`,
                        }}>{m.type}</span>
                        <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', width: 24, textAlign: 'right' }}>
                          {m.power ?? '—'}
                        </span>
                      </div>
                    )
                  })}
                  {filteredMoves.length === 0 && (
                    <div style={{ padding: '12px', fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      No moves match.
                    </div>
                  )}
                </div>
              </>
            ) : (
              /* Config view */
              <div style={{ padding: '14px 14px', overflowY: 'auto', flex: 1 }}>
                {/* 2×2 dropdowns */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 14 }}>
                  {/* Item — text input (no item list endpoint) */}
                  <div>
                    <div style={labelStyle}>Item</div>
                    <input
                      type="text"
                      value={draft.item}
                      onChange={(e) => setDraft((d) => ({ ...d, item: e.target.value }))}
                      style={inputStyle}
                      placeholder="e.g. Choice Scarf"
                    />
                  </div>
                  {/* Ability */}
                  <div>
                    <div style={labelStyle}>Ability</div>
                    <select
                      value={draft.ability}
                      onChange={(e) => setDraft((d) => ({ ...d, ability: e.target.value }))}
                      style={selectStyle}
                    >
                      <option value="">—</option>
                      {pokemon.abilities.map((a) => (
                        <option key={a.ability_id} value={a.ability_name}>{a.ability_name}</option>
                      ))}
                    </select>
                  </div>
                  {/* Nature */}
                  <div>
                    <div style={labelStyle}>Nature</div>
                    <select
                      value={draft.nature}
                      onChange={(e) => setDraft((d) => ({ ...d, nature: e.target.value }))}
                      style={selectStyle}
                    >
                      <option value="">—</option>
                      {NATURES.map((n) => <option key={n} value={n}>{titleCase(n)}</option>)}
                    </select>
                  </div>
                  {/* Tera Type */}
                  <div>
                    <div style={labelStyle}>Tera Type</div>
                    <select
                      value={draft.tera_type}
                      onChange={(e) => setDraft((d) => ({ ...d, tera_type: e.target.value }))}
                      style={selectStyle}
                    >
                      <option value="">—</option>
                      {TERA_TYPES.map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
                    </select>
                  </div>
                </div>

                {/* Move slots */}
                <div style={{ fontSize: 8, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-muted)', marginBottom: 6 }}>
                  Moveset
                </div>
                {([0, 1, 2, 3] as const).map((i) => {
                  const moveName = draft.moves[i]
                  const moveData = allMoves.find((m) => m.name === moveName)
                  const color = moveData?.type ? (TYPE_COLOR[moveData.type] ?? 'var(--text-muted)') : 'var(--border)'
                  return (
                    <div
                      key={i}
                      onClick={() => setPickingSlot(i)}
                      style={{
                        display: 'grid', gridTemplateColumns: '5px 1fr auto',
                        alignItems: 'center', gap: 8,
                        background: 'var(--surface-2)', border: '1px solid var(--border)',
                        borderRadius: 4, padding: '8px 10px', marginBottom: 5,
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--accent)' }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)' }}
                    >
                      <div style={{ width: 3, height: 18, borderRadius: 2, background: color }} />
                      <div>
                        <div style={{ fontSize: 11, fontWeight: 500 }}>
                          {moveName || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Empty slot</span>}
                        </div>
                        {moveData && (
                          <div style={{ fontSize: 8, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: 1, textTransform: 'uppercase' }}>
                            {moveData.category} · {moveData.type} · {moveData.power ?? '—'}
                          </div>
                        )}
                      </div>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>›</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Right column — stat distribution */}
          <div style={{ padding: '14px 14px', overflowY: 'auto' }}>
            <div style={{ fontSize: 8, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-muted)', marginBottom: 10 }}>
              Stat Distribution
            </div>

            {STAT_KEYS.map((key) => {
              const base = baseForStat(key)
              const ev = draft.evs[key]
              const mod = key === 'hp' ? 1 : natureMod(key)
              const finalVal = calcStat(base, ev, key === 'hp', mod)
              const isPlus = natureMods.plus === key
              const isMinus = natureMods.minus === key
              const labelColor = isPlus ? 'var(--accent)' : isMinus ? 'oklch(0.60 0.18 25)' : 'var(--text-muted)'

              return (
                <div key={key} style={{ display: 'grid', gridTemplateColumns: '32px 1fr 36px 36px', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: labelColor, textTransform: 'uppercase' }}>
                    {STAT_LABELS[key]}{isPlus ? '+' : isMinus ? '−' : ''}
                  </span>
                  <input
                    type="range"
                    min={0}
                    max={252}
                    step={4}
                    value={ev}
                    disabled={total >= 508 && ev === 0}
                    onChange={(e) => setEv(key, Number(e.target.value))}
                    style={{ width: '100%', accentColor: isPlus ? 'oklch(0.85 0.18 130)' : isMinus ? 'oklch(0.60 0.18 25)' : 'var(--accent)', cursor: total >= 508 && ev === 0 ? 'not-allowed' : 'pointer', opacity: total >= 508 && ev === 0 ? 0.35 : 1 }}
                  />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', textAlign: 'right' }}>
                    {ev}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, textAlign: 'right' }}>
                    {finalVal}
                  </span>
                </div>
              )
            })}

            {/* EV total bar */}
            <div style={{ marginTop: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ fontSize: 8, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>EV Total</span>
                <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: total > 508 ? 'oklch(0.60 0.18 25)' : 'var(--text-muted)' }}>
                  {total} / 508
                </span>
              </div>
              <div style={{ height: 3, background: 'var(--surface-2)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 2,
                  width: `${Math.min(100, (total / 508) * 100)}%`,
                  background: total > 508 ? 'oklch(0.60 0.18 25)' : 'var(--accent)',
                  transition: 'width 0.1s',
                }} />
              </div>
            </div>

            {/* EV presets */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 10 }}>
              {Object.entries(EV_PRESETS).map(([label, preset]) => (
                <button
                  key={label}
                  onClick={() => setDraft((d) => ({ ...d, evs: { ...d.evs, ...preset } }))}
                  style={{
                    fontSize: 9, fontFamily: 'var(--font-mono)', padding: '3px 8px',
                    background: 'var(--surface-2)', border: '1px solid var(--border)',
                    borderRadius: 3, cursor: 'pointer', color: 'var(--text-muted)',
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)' }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)' }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '12px 20px', borderTop: '1px solid var(--border)',
          background: 'var(--surface-2)',
        }}>
          <div>
            {saveError && (
              <span style={{ fontSize: 11, color: 'oklch(0.55 0.18 25)', fontFamily: 'var(--font-mono)' }}>
                {saveError}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={onClose}
              style={{
                fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                letterSpacing: '0.06em', background: 'none',
                border: '1px solid var(--border)', color: 'var(--text-muted)',
                borderRadius: 4, padding: '6px 16px', cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || evTotal(draft.evs) > 508}
              style={{
                fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
                letterSpacing: '0.06em', background: 'var(--accent)',
                color: 'var(--accent-fg)', border: 'none',
                borderRadius: 4, padding: '6px 16px', cursor: 'pointer',
                opacity: saving || evTotal(draft.evs) > 508 ? 0.5 : 1,
              }}
            >
              {saving ? '...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Shared style objects ──────────────────────────────────────────────────────

const labelStyle = {
  fontSize: 8, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' as const,
  letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: 3,
}

const inputStyle = {
  width: '100%', background: 'var(--surface-2)',
  border: '1px solid var(--border)', borderRadius: 3,
  padding: '4px 6px', fontFamily: 'var(--font-mono)',
  fontSize: 10, color: 'var(--text)', outline: 'none',
  boxSizing: 'border-box' as const,
}

const selectStyle = {
  width: '100%', background: 'var(--surface-2)',
  border: '1px solid var(--border)', borderRadius: 3,
  padding: '4px 6px', fontFamily: 'var(--font-mono)',
  fontSize: 10, color: 'var(--text)', outline: 'none',
  boxSizing: 'border-box' as const,
}
