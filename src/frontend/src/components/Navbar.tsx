import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/pokemon', label: 'Pokémon' },
  { to: '/generate', label: 'Generator' },
  { to: '/optimize', label: 'Optimizer' },
  { to: '/teams', label: 'Teams' },
  { to: '/regulations', label: 'Regulations' },
  { to: '/battle-results', label: 'Battles' },
]

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav
      className="flex items-center gap-6 px-5 py-3"
      style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}
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
      <div className="ml-auto flex items-center gap-4">
        {user ? (
          <>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {user.email}
            </span>
            <button
              onClick={handleLogout}
              className="text-sm"
              style={{ color: 'var(--text-muted)' }}
            >
              Logout
            </button>
          </>
        ) : (
          <>
            <NavLink
              to="/login"
              className="text-sm"
              style={{ color: 'var(--text-muted)' }}
            >
              Log in
            </NavLink>
            <NavLink
              to="/register"
              className="text-sm font-medium"
              style={{ color: 'var(--accent)' }}
            >
              Register
            </NavLink>
          </>
        )}
      </div>
    </nav>
  )
}
