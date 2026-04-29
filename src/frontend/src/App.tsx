import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import PokemonBrowser from './pages/PokemonBrowser'
import TeamGenerator from './pages/TeamGenerator'
import TeamOptimizer from './pages/TeamOptimizer'
import TeamAnalyzer from './pages/TeamAnalyzer'

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
          <Route path="/analyze" element={<TeamAnalyzer />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
