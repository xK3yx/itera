import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Register from '../pages/Register'

vi.mock('../store/authStore', () => ({
  default: vi.fn((selector) => {
    if (typeof selector === 'function') {
      return selector({
        register: vi.fn().mockResolvedValue({ success: true }),
        isLoading: false,
        error: null,
        clearError: vi.fn(),
      })
    }
    return {
      register: vi.fn().mockResolvedValue({ success: true }),
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    }
  })
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => vi.fn() }
})

describe('Register page', () => {
  it('renders all fields', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('renders create account button', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('renders link to login page', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument()
  })

  it('updates username field on change', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    const usernameInput = screen.getByLabelText('Username')
    fireEvent.change(usernameInput, { target: { value: 'testuser' } })
    expect(usernameInput.value).toBe('testuser')
  })
})