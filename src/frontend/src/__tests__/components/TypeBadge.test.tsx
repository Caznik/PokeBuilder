import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import TypeBadge from '../../components/TypeBadge'

describe('TypeBadge', () => {
  it('renders the type name', () => {
    render(<TypeBadge typeName="fire" />)
    expect(screen.getByText('fire')).toBeInTheDocument()
  })

  it('renders without crashing for an unknown type', () => {
    render(<TypeBadge typeName="cosmic" />)
    expect(screen.getByText('cosmic')).toBeInTheDocument()
  })

  it('uses sans-serif font, not monospace', () => {
    const { container } = render(<TypeBadge typeName="fire" />)
    const span = container.querySelector('span')!
    expect(span.style.fontFamily).toContain('Inter')
    expect(span.style.fontFamily).not.toContain('mono')
  })
})
