import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'
import PokemonBrowser from './pages/PokemonBrowser'
import TeamGenerator from './pages/TeamGenerator'
import TeamOptimizer from './pages/TeamOptimizer'
import Teams from './pages/Teams'
import TeamDetail from './pages/TeamDetail'
import Regulations from './pages/Regulations'
import Login from './pages/Login'
import Register from './pages/Register'

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return null

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <>
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/pokemon" replace />} />
          <Route path="/login" element={<Navigate to="/pokemon" replace />} />
          <Route path="/register" element={<Navigate to="/pokemon" replace />} />
          <Route path="/pokemon" element={<PokemonBrowser />} />
          <Route path="/generate" element={<TeamGenerator />} />
          <Route path="/optimize" element={<TeamOptimizer />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/teams/:id" element={<TeamDetail />} />
          <Route path="/regulations" element={<Regulations />} />
          <Route path="/build" element={<Navigate to="/teams" replace />} />
          <Route path="/analyze" element={<Navigate to="/teams" replace />} />
          <Route path="/saved" element={<Navigate to="/teams?tab=saved" replace />} />
        </Routes>
      </main>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
