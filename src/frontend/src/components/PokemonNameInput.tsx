import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'
import type { Pokemon } from '../api/types'

function titleCase(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

interface Props {
  value: string
  onChange: (value: string) => void
  onSelect?: (selectedName: string) => void
  placeholder?: string
  disabled?: boolean
  className?: string
}

export default function PokemonNameInput({ value, onChange, onSelect, placeholder, disabled, className }: Props) {
  const [suggestions, setSuggestions] = useState<Pokemon[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const suppressRef = useRef(false)

  useEffect(() => {
    const token = value.trim()
    if (!token) {
      setSuggestions([])
      setShowSuggestions(false)
      return
    }
    const timer = setTimeout(() => {
      api.pokemon.list(1, 8, token)
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
  }, [value])

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
    onChange(name)
    setShowSuggestions(false)
    onSelect?.(name)
  }

  return (
    <div ref={containerRef} className="relative flex-1">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true) }}
        placeholder={placeholder}
        disabled={disabled}
        className={className}
      />
      {showSuggestions && (
        <ul className="absolute z-10 w-full mt-1 bg-gray-800 border border-gray-600 rounded shadow-lg overflow-hidden">
          {suggestions.map((p) => (
            <li
              key={p.id}
              onMouseDown={() => handleSelect(p.name)}
              className="px-3 py-2 text-sm text-gray-200 hover:bg-gray-700 cursor-pointer flex items-center justify-between"
            >
              <span>{titleCase(p.name)}</span>
              <span className="text-xs text-gray-500">Gen {p.generation ?? '?'}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
