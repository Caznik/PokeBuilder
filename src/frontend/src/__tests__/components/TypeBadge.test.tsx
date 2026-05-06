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
})
