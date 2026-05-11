// src/frontend/src/pages/Login.tsx
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(
    searchParams.get('error') === 'oauth_failed'
      ? 'Google sign-in failed. Please try again.'
      : null
  )
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login({ email, password })
      navigate('/teams', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-16">
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text)' }}>
        Log in
      </h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
          className="px-3 py-2 rounded border text-sm"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          className="px-3 py-2 rounded border text-sm"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}
        />
        <button
          type="submit"
          disabled={loading}
          className="py-2 rounded text-sm font-medium transition-opacity"
          style={{ background: 'var(--accent)', color: '#fff', opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      {error && (
        <p className="mt-3 text-sm" style={{ color: 'var(--error, #ef4444)' }}>{error}</p>
      )}
      <div className="my-4 flex items-center gap-2">
        <hr className="flex-1" style={{ borderColor: 'var(--border)' }} />
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>or</span>
        <hr className="flex-1" style={{ borderColor: 'var(--border)' }} />
      </div>
      <button
        type="button"
        onClick={() => { window.location.href = '/api/auth/google' }}
        className="w-full py-2 rounded border text-sm font-medium"
        style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}
      >
        Sign in with Google
      </button>
      <p className="mt-4 text-sm" style={{ color: 'var(--text-muted)' }}>
        No account?{' '}
        <Link to="/register" style={{ color: 'var(--accent)' }}>
          Register
        </Link>
      </p>
    </div>
  )
}
