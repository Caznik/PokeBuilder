// src/frontend/src/context/AuthContext.tsx
import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { User, LoginRequest, RegisterRequest } from '../api/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (data: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.auth.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(data: LoginRequest): Promise<void> {
    const u = await api.auth.login(data)
    setUser(u)
  }

  async function register(data: RegisterRequest): Promise<void> {
    const u = await api.auth.register(data)
    setUser(u)
  }

  async function logout(): Promise<void> {
    await api.auth.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
