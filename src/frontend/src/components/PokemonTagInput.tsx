import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { Pokemon } from '../api/types'

const DEFAULT_MAX = 6

function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

function countNames(value: string): number {
  return value.split(',').map((s) => s.trim()).filter(Boolean).length
}

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  label?: string
  maxNames?: number
}

export default function PokemonTagInput({ value, onChange, placeholder, label, maxNames = DEFAULT_MAX }: Props) {
  const [suggestions, setSuggestions] = useState<Pokemon[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const suppressRef = useRef(false)

  // Split into confirmed names (before last comma) vs current in-progress token
  const parts = value.split(',')
  const completedNames = parts.slice(0, -1).map((s) => s.trim()).filter(Boolean)
  const currentToken = parts[parts.length - 1].trimStart()
  const nameCount = completedNames.length + (currentToken ? 1 : 0)

  // At max only when all 6 slots are committed (trailing comma present after 6th name)
  const isAtMax = completedNames.length >= maxNames

  function applyChange(newValue: string) {
    // Block changes that would push the confirmed+current count above maxNames
    if (countNames(newValue) > maxNames) return
    onChange(newValue)
  }

  useEffect(() => {
    if (!currentToken || isAtMax) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }
    const timer = setTimeout(() => {
      api.pokemon.list(1, 8, currentToken)
        .then((d) => {
          setSuggestions(d.items)
          if (!suppressRef.current) {
            setShowSuggestions(d.items.length > 0)
          }
          suppressRef.current = false
        })
        .catch(() => { suppressRef.current = false })
    }, 150)
    return () => clearTimeout(timer)
  }, [currentToken, isAtMax])

  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [])

  function handleSelect(name: string) {
    suppressRef.current = true
    const parts = value.split(',')
    parts[parts.length - 1] = ' ' + name
    const joined = parts.join(',')
    // Don't append trailing ", " if this selection fills the last slot
    const next = countNames(joined) >= maxNames ? joined.trimStart() : joined + ', '
    applyChange(next)
    setShowSuggestions(false)
  }

  const counterColor =
    nameCount >= maxNames ? 'text-red-400' :
    nameCount >= maxNames - 1 ? 'text-yellow-400' :
    'text-gray-500'

  return (
    <div ref={containerRef}>
      {label && (
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400">{label}</label>
          {isFinite(maxNames) && (
            <span className={`text-xs font-medium ${counterColor}`}>{nameCount}/{maxNames}</span>
          )}
        </div>
      )}
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => applyChange(e.target.value)}
          onFocus={() => { if (suggestions.length > 0 && !isAtMax) setShowSuggestions(true) }}
          placeholder={isAtMax ? 'Remove a Pokémon to add more' : placeholder}
          className="w-full rounded px-3 py-2 text-sm placeholder-gray-500 transition-colors"
          style={{
            background: 'var(--surface-2)',
            border: isAtMax ? '1px solid oklch(0.45 0.12 25)' : '1px solid var(--border-subtle)',
            color: isAtMax ? 'var(--text-muted)' : 'var(--text)',
          }}
        />
        {showSuggestions && !isAtMax && (
          <ul className="absolute z-10 w-full mt-1 rounded shadow-lg overflow-hidden" style={{ background: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
            {suggestions.map((p) => (
              <li
                key={p.id}
                onMouseDown={() => handleSelect(p.name)}
                className="px-3 py-2 text-sm cursor-pointer flex items-center justify-between transition-colors hover:bg-white/5" style={{ color: 'var(--text)' }}
              >
                <span>{titleCase(p.name)}</span>
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>Gen {p.generation ?? '?'}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      {isAtMax && (
        <p className="text-xs text-red-400 mt-1">Max {maxNames} Pokémon reached. Delete a name to add another.</p>
      )}
    </div>
  )
}
