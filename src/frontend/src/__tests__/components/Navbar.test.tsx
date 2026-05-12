import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Navbar from '../../components/Navbar'

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn() }),
}))

function renderNavbar() {
  return render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>
  )
}

describe('Navbar theme toggle', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.className = ''
  })

  afterEach(cleanup)

  it('defaults to dark mode (no light class on html)', () => {
    renderNavbar()
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('clicking the toggle switches to light mode', async () => {
    renderNavbar()
    const toggle = screen.getByRole('button', { name: /toggle theme/i })
    await userEvent.click(toggle)
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })

  it('clicking toggle twice returns to dark mode', async () => {
    renderNavbar()
    const toggle = screen.getByRole('button', { name: /toggle theme/i })
    await userEvent.click(toggle)
    await userEvent.click(toggle)
    expect(document.documentElement.classList.contains('light')).toBe(false)
  })

  it('persists theme preference to localStorage', async () => {
    renderNavbar()
    const toggle = screen.getByRole('button', { name: /toggle theme/i })
    await userEvent.click(toggle)
    expect(localStorage.getItem('theme')).toBe('light')
    await userEvent.click(toggle)
    expect(localStorage.getItem('theme')).toBe('dark')
  })

  it('reads initial theme from localStorage', () => {
    localStorage.setItem('theme', 'light')
    renderNavbar()
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })
})
