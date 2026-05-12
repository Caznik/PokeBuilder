import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { BattleLogOut, Regulation, SavedTeamSummary } from '../api/types'
import PokemonTagInput from '../components/PokemonTagInput'

function spriteUrl(name: string) {
  return `https://img.pokemondb.net/sprites/home/normal/${name}.png`
}

function titleCase(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

function resultColor(result: string): string {
  if (result === 'win') return 'oklch(0.65 0.15 145)'
  if (result === 'loss') return 'oklch(0.6 0.18 25)'
  return 'oklch(0.75 0.12 85)'
}

type FormatType = 'singles' | 'vgc'
type ResultType = 'win' | 'loss' | 'tie' | ''

export default function BattleResults() {
  // Data
  const [logs, setLogs] = useState<BattleLogOut[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logsError, setLogsError] = useState<string | null>(null)
  const [regulations, setRegulations] = useState<Regulation[]>([])
  const [savedTeams, setSavedTeams] = useState<SavedTeamSummary[]>([])

  // Form visibility
  const [formOpen, setFormOpen] = useState(false)

  // Form fields
  const [selectedTeamId, setSelectedTeamId] = useState<number | ''>('')
  const [regulationId, setRegulationId] = useState<number | ''>('')
  const [format, setFormat] = useState<FormatType>('singles')
  const [broughtPokemon, setBroughtPokemon] = useState<string[]>([])
  const [enemyTeamStr, setEnemyTeamStr] = useState('')
  const [enemyBrought, setEnemyBrought] = useState<string[]>([])
  const [result, setResult] = useState<ResultType>('')
  const [notes, setNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Filter state
  const [filterRegulation, setFilterRegulation] = useState('')
  const [filterFormat, setFilterFormat] = useState('')
  const [filterResult, setFilterResult] = useState('')

  const maxBrought = format === 'singles' ? 3 : 4

  function fetchLogs(reg?: string, fmt?: string, res?: string) {
    setLogsLoading(true)
    setLogsError(null)
    const filters: { regulation_id?: number; format?: string; result?: string } = {}
    if (reg) filters.regulation_id = Number(reg)
    if (fmt) filters.format = fmt
    if (res) filters.result = res
    api.battleLogs.list(Object.keys(filters).length ? filters : undefined)
      .then(setLogs)
      .catch((e: unknown) => setLogsError(e instanceof Error ? e.message : 'Failed to load logs'))
      .finally(() => setLogsLoading(false))
  }

  useEffect(() => {
    api.regulations.list().then(setRegulations).catch(() => setRegulations([]))
    api.savedTeams.list().then(setSavedTeams).catch(() => setSavedTeams([]))
    fetchLogs()
  }, [])

  useEffect(() => {
    const regFilter = regulationId !== '' ? Number(regulationId) : undefined
    api.savedTeams.list(regFilter).then((teams) => {
      setSavedTeams(teams)
      if (selectedTeamId !== '' && !teams.some((t) => t.id === Number(selectedTeamId))) {
        setSelectedTeamId('')
        setBroughtPokemon([])
      }
    }).catch(() => setSavedTeams([]))
  }, [regulationId])

  function handleTeamChange(teamIdStr: string) {
    setSelectedTeamId(teamIdStr === '' ? '' : Number(teamIdStr))
    setBroughtPokemon([])
  }

  function handleFormatChange(fmt: FormatType) {
    setFormat(fmt)
    setBroughtPokemon([])
    setEnemyBrought([])
  }

  function toggleEnemyBrought(name: string) {
    if (enemyBrought.includes(name)) {
      setEnemyBrought(enemyBrought.filter((p) => p !== name))
    } else if (enemyBrought.length < maxBrought) {
      setEnemyBrought([...enemyBrought, name])
    }
  }

  function toggleBrought(name: string) {
    if (broughtPokemon.includes(name)) {
      setBroughtPokemon(broughtPokemon.filter((p) => p !== name))
    } else if (broughtPokemon.length < maxBrought) {
      setBroughtPokemon([...broughtPokemon, name])
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)

    const enemyList = enemyTeamStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

    if (broughtPokemon.length !== maxBrought) {
      setFormError(`Select exactly ${maxBrought} Pokémon you brought.`)
      return
    }
    if (enemyList.length < 1 || enemyList.length > 6) {
      setFormError('Enemy team must have 1–6 Pokémon.')
      return
    }
    if (!result) {
      setFormError('Select a result.')
      return
    }

    setSubmitting(true)
    try {
      await api.battleLogs.create({
        saved_team_id: selectedTeamId !== '' ? Number(selectedTeamId) : null,
        regulation_id: regulationId !== '' ? Number(regulationId) : null,
        format,
        brought_pokemon: broughtPokemon,
        enemy_team: enemyList,
        enemy_brought: enemyBrought,
        result: result as 'win' | 'loss' | 'tie',
        notes: notes.trim() || null,
      })
      // Reset form
      setSelectedTeamId('')
      setRegulationId('')
      setFormat('singles')
      setBroughtPokemon([])
      setEnemyTeamStr('')
      setEnemyBrought([])
      setResult('')
      setNotes('')
      setFormOpen(false)
      fetchLogs(filterRegulation, filterFormat, filterResult)
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Failed to log battle.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(id: number) {
    try {
      await api.battleLogs.delete(id)
      fetchLogs(filterRegulation, filterFormat, filterResult)
    } catch { /* ignore */ }
  }

  function handleFilterChange(reg: string, fmt: string, res: string) {
    setFilterRegulation(reg)
    setFilterFormat(fmt)
    setFilterResult(res)
    fetchLogs(reg, fmt, res)
  }

  const selectedTeam = savedTeams.find((t) => t.id === Number(selectedTeamId))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold" style={{ color: 'var(--text)' }}>
          Battle Results
        </h1>
        <button
          onClick={() => setFormOpen((o) => !o)}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{ background: 'var(--accent)', color: 'var(--surface)' }}
        >
          {formOpen ? 'Cancel' : '+ Log Battle'}
        </button>
      </div>

      {/* Log Battle Form */}
      {formOpen && (
        <form
          onSubmit={handleSubmit}
          className="rounded-lg p-5 space-y-4"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <h2 className="text-base font-semibold" style={{ color: 'var(--text)' }}>
            Log a Battle
          </h2>

          {/* Regulation selector */}
          <div>
            <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
              Regulation (optional)
            </label>
            <select
              value={regulationId}
              onChange={(e) => setRegulationId(e.target.value === '' ? '' : Number(e.target.value))}
              className="w-full rounded px-3 py-2 text-sm"
              style={{
                background: 'var(--surface-2)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text)',
              }}
            >
              <option value="">— no regulation —</option>
              {regulations.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          {/* Team selector */}
          <div>
            <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
              My Team (optional)
            </label>
            <select
              value={selectedTeamId}
              onChange={(e) => handleTeamChange(e.target.value)}
              className="w-full rounded px-3 py-2 text-sm"
              style={{
                background: 'var(--surface-2)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text)',
              }}
            >
              <option value="">— no team —</option>
              {savedTeams.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          {/* Format tabs */}
          <div>
            <label className="block text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
              Format
            </label>
            <div className="flex gap-2">
              {(['singles', 'vgc'] as FormatType[]).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => handleFormatChange(f)}
                  className="px-4 py-1.5 rounded-full text-sm font-medium transition-colors"
                  style={{
                    background: format === f ? 'var(--accent)' : 'var(--surface-2)',
                    color: format === f ? 'var(--surface)' : 'var(--text-muted)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  {f === 'singles' ? 'Singles' : 'VGC'}
                </button>
              ))}
            </div>
          </div>

          {/* Pokémon I brought */}
          {selectedTeam && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Pokémon I brought
                </label>
                <span
                  className="text-xs font-medium"
                  style={{
                    color: broughtPokemon.length === maxBrought
                      ? 'oklch(0.65 0.15 145)'
                      : 'var(--text-muted)',
                  }}
                >
                  {broughtPokemon.length}/{maxBrought}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedTeam.members.map((m) => {
                  const checked = broughtPokemon.includes(m.pokemon_name)
                  const disabled = !checked && broughtPokemon.length >= maxBrought
                  return (
                    <label
                      key={m.slot}
                      className="flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer text-sm transition-colors"
                      style={{
                        background: checked ? 'var(--accent)' : 'var(--surface-2)',
                        color: checked ? 'var(--surface)' : disabled ? 'var(--text-muted)' : 'var(--text)',
                        border: '1px solid var(--border-subtle)',
                        opacity: disabled ? 0.5 : 1,
                        cursor: disabled ? 'not-allowed' : 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        className="hidden"
                        checked={checked}
                        disabled={disabled}
                        onChange={() => toggleBrought(m.pokemon_name)}
                      />
                      <img
                        src={spriteUrl(m.pokemon_name)}
                        alt={m.pokemon_name}
                        className="w-6 h-6 object-contain"
                      />
                      {titleCase(m.pokemon_name)}
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {/* Enemy team */}
          <PokemonTagInput
            value={enemyTeamStr}
            onChange={(v) => { setEnemyTeamStr(v); setEnemyBrought([]) }}
            label="Enemy team (full)"
            maxNames={6}
            placeholder="Type Pokémon name…"
          />

          {/* Enemy brought */}
          {enemyTeamStr.trim() && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Enemy Pokémon brought
                </label>
                <span
                  className="text-xs font-medium"
                  style={{
                    color: enemyBrought.length === maxBrought
                      ? 'oklch(0.65 0.15 145)'
                      : 'var(--text-muted)',
                  }}
                >
                  {enemyBrought.length}/{maxBrought}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {enemyTeamStr.split(',').map((s) => s.trim()).filter(Boolean).map((name) => {
                  const checked = enemyBrought.includes(name)
                  const disabled = !checked && enemyBrought.length >= maxBrought
                  return (
                    <label
                      key={name}
                      className="flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer text-sm transition-colors"
                      style={{
                        background: checked ? 'oklch(0.6 0.18 25)' : 'var(--surface-2)',
                        color: checked ? '#fff' : disabled ? 'var(--text-muted)' : 'var(--text)',
                        border: '1px solid var(--border-subtle)',
                        opacity: disabled ? 0.5 : 1,
                        cursor: disabled ? 'not-allowed' : 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        className="hidden"
                        checked={checked}
                        disabled={disabled}
                        onChange={() => toggleEnemyBrought(name)}
                      />
                      <img
                        src={spriteUrl(name)}
                        alt={name}
                        className="w-6 h-6 object-contain"
                      />
                      {titleCase(name)}
                    </label>
                  )
                })}
              </div>
            </div>
          )}

          {/* Result toggle */}
          <div>
            <label className="block text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
              Result
            </label>
            <div className="flex gap-2">
              {(['win', 'loss', 'tie'] as const).map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setResult(r)}
                  className="px-4 py-1.5 rounded text-sm font-medium transition-colors"
                  style={{
                    background: result === r ? resultColor(r) : 'var(--surface-2)',
                    color: result === r ? '#fff' : 'var(--text-muted)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  {titleCase(r)}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full rounded px-3 py-2 text-sm resize-y"
              style={{
                background: 'var(--surface-2)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text)',
              }}
              placeholder="Any notes about this battle…"
            />
          </div>

          {formError && (
            <p className="text-sm" style={{ color: 'oklch(0.6 0.18 25)' }}>
              {formError}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="px-5 py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: 'var(--accent)',
              color: 'var(--surface)',
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? 'Saving…' : 'Save Battle'}
          </button>
        </form>
      )}

      {/* Filters */}
      <div
        className="flex flex-wrap gap-3 items-center p-4 rounded-lg"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
      >
        <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          Filter:
        </span>
        <select
          value={filterRegulation}
          onChange={(e) => handleFilterChange(e.target.value, filterFormat, filterResult)}
          className="rounded px-2 py-1 text-sm"
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text)',
          }}
        >
          <option value="">All regulations</option>
          {regulations.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select
          value={filterFormat}
          onChange={(e) => handleFilterChange(filterRegulation, e.target.value, filterResult)}
          className="rounded px-2 py-1 text-sm"
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text)',
          }}
        >
          <option value="">All formats</option>
          <option value="singles">Singles</option>
          <option value="vgc">VGC</option>
        </select>
        <select
          value={filterResult}
          onChange={(e) => handleFilterChange(filterRegulation, filterFormat, e.target.value)}
          className="rounded px-2 py-1 text-sm"
          style={{
            background: 'var(--surface-2)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text)',
          }}
        >
          <option value="">All results</option>
          <option value="win">Win</option>
          <option value="loss">Loss</option>
          <option value="tie">Tie</option>
        </select>
      </div>

      {/* Battle History */}
      <div>
        <h2 className="text-base font-semibold mb-3" style={{ color: 'var(--text)' }}>
          Battle History
        </h2>

        {logsLoading && (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading…</p>
        )}
        {logsError && (
          <p className="text-sm" style={{ color: 'oklch(0.6 0.18 25)' }}>{logsError}</p>
        )}

        {!logsLoading && !logsError && logs.length === 0 && (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            No battles logged yet.
          </p>
        )}

        <div className="space-y-3">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-lg p-4 space-y-3"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              {/* Header row: format | result | team name | date | delete */}
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="px-2 py-0.5 rounded text-xs font-medium uppercase"
                  style={{ background: 'var(--surface-2)', color: 'var(--text-muted)' }}
                >
                  {log.format}
                </span>
                <span
                  className="px-2 py-0.5 rounded text-xs font-semibold uppercase"
                  style={{ background: resultColor(log.result), color: 'oklch(1 0 0)' }}
                >
                  {log.result}
                </span>
                {log.saved_team_name && (
                  <span className="text-sm font-medium" style={{ color: 'var(--text)' }}>
                    {log.saved_team_name}
                  </span>
                )}
                <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
                  {new Date(log.played_at).toLocaleDateString()}
                </span>
                <button
                  onClick={() => handleDelete(log.id)}
                  className="text-xs px-2 py-1 rounded transition-colors"
                  style={{
                    background: 'var(--surface-2)',
                    color: 'var(--text-muted)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  Delete
                </button>
              </div>

              {/* Battle row: my full team → my brought  vs  enemy brought ← enemy full team */}
              <div className="flex items-center gap-2 flex-wrap text-xs" style={{ color: 'var(--text-muted)' }}>
                {/* My full team (dimmed) */}
                {log.saved_team_members.length > 0 && (
                  <div className="flex items-center gap-0.5">
                    {log.saved_team_members.map((name) => (
                      <img key={name} src={spriteUrl(name)} alt={name} title={titleCase(name)} className="w-8 h-8 object-contain opacity-40" />
                    ))}
                  </div>
                )}

                {/* Arrow inward */}
                {log.saved_team_members.length > 0 && <span className="font-bold">→</span>}

                {/* My brought */}
                <div className="flex items-center gap-0.5">
                  {log.brought_pokemon.map((name) => (
                    <img key={name} src={spriteUrl(name)} alt={name} title={titleCase(name)} className="w-9 h-9 object-contain" />
                  ))}
                </div>

                <span className="px-1 font-semibold" style={{ color: 'var(--text)' }}>vs</span>

                {/* Enemy brought */}
                <div className="flex items-center gap-0.5">
                  {log.enemy_brought.length > 0
                    ? log.enemy_brought.map((name) => (
                        <img key={name} src={spriteUrl(name)} alt={name} title={titleCase(name)} className="w-9 h-9 object-contain" />
                      ))
                    : log.enemy_team.map((name) => (
                        <img key={name} src={spriteUrl(name)} alt={name} title={titleCase(name)} className="w-9 h-9 object-contain" />
                      ))}
                </div>

                {/* Arrow inward */}
                <span className="font-bold">←</span>

                {/* Enemy full team */}
                <div className="flex items-center gap-0.5">
                  {log.enemy_team.map((name) => (
                    <img key={name} src={spriteUrl(name)} alt={name} title={titleCase(name)} className="w-8 h-8 object-contain opacity-40" />
                  ))}
                </div>
              </div>

              {/* Notes */}
              {log.notes && (
                <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
                  {log.notes}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
