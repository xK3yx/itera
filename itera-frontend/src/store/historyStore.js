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
    } catch (err) {
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
    } catch (err) {
      return null
    }
  },
}))

export default useHistoryStore