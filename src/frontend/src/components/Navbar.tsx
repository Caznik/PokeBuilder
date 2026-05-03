import { NavLink } from 'react-router-dom'

const links = [
  { to: '/pokemon', label: 'Pokémon' },
  { to: '/generate', label: 'Generator' },
  { to: '/optimize', label: 'Optimizer' },
  { to: '/teams', label: 'Teams' },
  { to: '/regulations', label: 'Regulations' },
]

export default function Navbar() {
  return (
    <nav
      className="flex items-center gap-6 px-5 py-3"
      style={{
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <span
        className="mr-4 font-mono font-semibold text-base tracking-tight"
        style={{ color: 'var(--accent)' }}
      >
        PokéBuilder
      </span>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className="text-sm transition-colors"
          style={({ isActive }) => ({
            color: isActive ? 'var(--accent)' : 'var(--text-muted)',
            fontWeight: isActive ? 600 : 400,
          })}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
