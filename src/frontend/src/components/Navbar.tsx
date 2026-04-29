import { NavLink } from 'react-router-dom'

const links = [
  { to: '/pokemon', label: 'Pokémon' },
  { to: '/generate', label: 'Generator' },
  { to: '/optimize', label: 'Optimizer' },
  { to: '/analyze', label: 'Analyzer' },
]

export default function Navbar() {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center gap-6">
      <span className="text-blue-400 font-bold text-lg mr-4">PokeBuilder</span>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            isActive
              ? 'text-blue-400 font-semibold text-sm'
              : 'text-gray-400 hover:text-gray-200 text-sm'
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
