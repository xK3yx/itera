import { create } from 'zustand'
import api from '../services/api'

const useChatStore = create((set, get) => ({
  sessionId: null,
  messages: [],
  roadmap: null,
  isLoading: false,
  isTyping: false,
  error: null,

  startSession: async (title = 'New Learning Session') => {
    set({ isLoading: true, error: null })
    try {
      const res = await api.post('/chat/start', { title })
      set({ sessionId: res.data.session_id, messages: [], roadmap: null, isLoading: false })
      return { success: true }
    } catch (err) {
      set({ error: 'Failed to start session', isLoading: false })
      return { success: false }
    }
  },

  sendMessage: async (text) => {
    const { sessionId } = get()
    if (!sessionId) return

    // Add user message immediately
    const userMessage = { role: 'user', content: text, id: Date.now() }
    set((state) => ({ messages: [...state.messages, userMessage], isTyping: true }))

    try {
      const res = await api.post(`/chat/${sessionId}/message`, { message: text })
      const data = res.data

      // Add assistant message
      const assistantMessage = {
        role: 'assistant',
        content: data.message,
        id: Date.now() + 1,
      }
      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isTyping: false,
        roadmap: data.roadmap || state.roadmap,
      }))
    } catch (err) {
      set((state) => ({
        messages: [...state.messages, {
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          id: Date.now() + 1,
          isError: true,
        }],
        isTyping: false,
      }))
    }
  },

  clearSession: () => {
    set({ sessionId: null, messages: [], roadmap: null, error: null })
  },
}))

export default useChatStore