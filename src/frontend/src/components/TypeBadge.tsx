const TYPE_COLORS: Record<string, string> = {
  fire: 'bg-orange-600 text-white',
  water: 'bg-blue-500 text-white',
  grass: 'bg-green-600 text-white',
  electric: 'bg-yellow-400 text-black',
  psychic: 'bg-pink-500 text-white',
  ice: 'bg-cyan-400 text-black',
  dragon: 'bg-indigo-700 text-white',
  dark: 'bg-gray-800 text-white border border-gray-600',
  fairy: 'bg-pink-300 text-black',
  fighting: 'bg-red-700 text-white',
  poison: 'bg-purple-600 text-white',
  ground: 'bg-yellow-700 text-white',
  flying: 'bg-sky-400 text-black',
  bug: 'bg-lime-600 text-white',
  rock: 'bg-stone-500 text-white',
  ghost: 'bg-violet-800 text-white',
  steel: 'bg-slate-400 text-black',
  normal: 'bg-gray-400 text-black',
}

interface TypeBadgeProps {
  typeName: string
}

export default function TypeBadge({ typeName }: TypeBadgeProps) {
  const color = TYPE_COLORS[typeName.toLowerCase()] ?? 'bg-gray-600 text-white'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium capitalize ${color}`}>
      {typeName}
    </span>
  )
}
