import { create } from 'zustand'
import api from '../services/api'

const useHistoryStore = create((set) => ({
  sessions: [],
  isLoading: false,

  fetchSessions: async () => {
    set({ isLoading: true })
    try {
      const res = await api.get('/roadmap/')
      set({ sessions: res.data || [], isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  loadSession: async (sessionId) => {
    try {
      const [historyRes, roadmapRes] = await Promise.all([
        api.get(`/chat/${sessionId}/history`),
        api.get(`/roadmap/${sessionId}`),
      ])
      return {
        messages: historyRes.data.messages || [],
        roadmap: roadmapRes.data.roadmap || null,
        sessionId,
      }
    } catch {
      return null
    }
  },

  deleteSession: async (sessionId) => {
    try {
      await api.delete(`/chat/${sessionId}`)
      set((state) => ({
        sessions: state.sessions.filter((s) => s.session_id !== sessionId),
      }))
      return true
    } catch {
      return false
    }
  },
}))

export default useHistoryStore