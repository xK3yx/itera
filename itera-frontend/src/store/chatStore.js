import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

const useChatStore = create(
  persist(
    (set, get) => ({
      sessionId: null,
      messages: [],
      roadmap: null,
      roadmapMessageCount: null,
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

        const userMessage = { role: 'user', content: text, id: Date.now() }
        set((state) => ({ messages: [...state.messages, userMessage], isTyping: true }))

        try {
          const res = await api.post(`/chat/${sessionId}/message`, { message: text })
          const data = res.data

          const assistantMessage = {
            role: 'assistant',
            content: data.message,
            id: Date.now() + 1,
          }
          set((state) => {
            const newMessages = [...state.messages, assistantMessage]
            return {
              messages: newMessages,
              isTyping: false,
              roadmap: data.roadmap || state.roadmap,
              roadmapMessageCount: data.roadmap ? newMessages.length : state.roadmapMessageCount,
            }
          })
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

      loadFromHistory: ({ sessionId, messages, roadmap }) => {
        const formatted = messages.map((m, i) => ({
          role: m.role,
          content: m.content,
          id: i,
        }))
        set({
          sessionId,
          messages: formatted,
          roadmap,
          // All loaded messages are pre-roadmap; follow-ups will appear below
          roadmapMessageCount: roadmap ? formatted.length : null,
        })
      },

      updateRoadmap: (newRoadmap) => set({ roadmap: newRoadmap }),

      clearSession: () => {
        set({ sessionId: null, messages: [], roadmap: null, roadmapMessageCount: null, error: null })
      },
    }),
    {
      name: 'itera-chat',
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
        roadmap: state.roadmap,
        roadmapMessageCount: state.roadmapMessageCount,
      }),
    }
  )
)

export default useChatStore