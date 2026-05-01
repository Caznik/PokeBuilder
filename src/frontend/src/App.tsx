import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import PokemonBrowser from './pages/PokemonBrowser'
import TeamGenerator from './pages/TeamGenerator'
import TeamOptimizer from './pages/TeamOptimizer'
import Teams from './pages/Teams'
import TeamDetail from './pages/TeamDetail'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/pokemon" replace />} />
          <Route path="/pokemon" element={<PokemonBrowser />} />
          <Route path="/generate" element={<TeamGenerator />} />
          <Route path="/optimize" element={<TeamOptimizer />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/teams/:id" element={<TeamDetail />} />
          <Route path="/build" element={<Navigate to="/teams" replace />} />
          <Route path="/analyze" element={<Navigate to="/teams" replace />} />
          <Route path="/saved" element={<Navigate to="/teams?tab=saved" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
