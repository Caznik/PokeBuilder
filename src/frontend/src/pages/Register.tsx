// src/frontend/src/pages/Register.tsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await register({ email, password })
      navigate('/teams', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-sm mx-auto mt-16">
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text)' }}>
        Create account
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
          placeholder="Password (8+ characters)"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          minLength={8}
          className="px-3 py-2 rounded border text-sm"
          style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}
        />
        {error && (
          <p className="text-sm" style={{ color: 'var(--error, #ef4444)' }}>{error}</p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="py-2 rounded text-sm font-medium transition-opacity"
          style={{ background: 'var(--accent)', color: '#fff', opacity: loading ? 0.7 : 1 }}
        >
          {loading ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="mt-4 text-sm" style={{ color: 'var(--text-muted)' }}>
        Have an account?{' '}
        <Link to="/login" style={{ color: 'var(--accent)' }}>
          Log in
        </Link>
      </p>
    </div>
  )
}
