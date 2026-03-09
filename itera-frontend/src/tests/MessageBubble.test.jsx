import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../components/MessageBubble'

describe('MessageBubble', () => {
  it('renders user message correctly', () => {
    const msg = { id: 1, role: 'user', content: 'Hello!' }
    render(<MessageBubble message={msg} />)
    expect(screen.getByText('Hello!')).toBeInTheDocument()
    expect(screen.getByText('You')).toBeInTheDocument()
  })

  it('renders assistant message correctly', () => {
    const msg = { id: 2, role: 'assistant', content: 'Hi there!' }
    render(<MessageBubble message={msg} />)
    expect(screen.getByText('Hi there!')).toBeInTheDocument()
    expect(screen.getByText('AI')).toBeInTheDocument()
  })
})