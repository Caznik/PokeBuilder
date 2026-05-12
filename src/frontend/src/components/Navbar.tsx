import { useState, useEffect } from 'react'
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
  // Navbar is the layout singleton — theme state lives here rather than in a page
  // because it's app-wide and the toggle is rendered here.
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') ?? 'dark'
  })

  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.classList.add('light')
    } else {
      document.documentElement.classList.remove('light')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  function toggleTheme() {
    setTheme(t => (t === 'dark' ? 'light' : 'dark'))
  }

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
        className="mr-4 font-sans font-bold text-base tracking-tight"
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
        {/* Theme toggle pill */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          aria-pressed={theme === 'light'}
          style={{
            width: 28,
            height: 16,
            borderRadius: 999,
            background: theme === 'light' ? 'var(--accent)' : 'var(--border)',
            border: 'none',
            cursor: 'pointer',
            padding: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: theme === 'light' ? 'flex-end' : 'flex-start',
            flexShrink: 0,
          }}
        >
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: theme === 'dark' ? 'var(--accent-fg)' : 'var(--surface)',
              display: 'block',
            }}
          />
        </button>

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
