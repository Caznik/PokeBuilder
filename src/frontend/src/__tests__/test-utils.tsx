import React from 'react'
import { render, type RenderResult } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

export function renderWithRouter(
  ui: React.ReactElement,
  { route = '/', path }: { route?: string; path?: string } = {}
): RenderResult {
  if (path) {
    return render(
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
        </Routes>
      </MemoryRouter>
    )
  }
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>
  )
}
