import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

const useProgressStore = create(
  persist(
    (set, get) => ({
      // { [sessionId]: string[] } — topic keys that are completed
      completedTopics: {},

      isCompleted: (sessionId, topicKey) => {
        const keys = get().completedTopics[sessionId] || []
        return keys.includes(topicKey)
      },

      toggleTopic: async (sessionId, topicKey) => {
        const current = get().completedTopics[sessionId] || []
        const isNowCompleted = !current.includes(topicKey)
        const updated = isNowCompleted
          ? [...current, topicKey]
          : current.filter((k) => k !== topicKey)

        // Optimistic update — immediately reflect in UI
        set((state) => ({
          completedTopics: { ...state.completedTopics, [sessionId]: updated },
        }))

        // Persist to backend
        try {
          await api.patch(`/roadmap/${sessionId}/progress`, {
            completed_topics: updated,
          })
        } catch {
          // Rollback on failure
          set((state) => ({
            completedTopics: { ...state.completedTopics, [sessionId]: current },
          }))
        }
      },

      clearProgress: (sessionId) => {
        set((state) => {
          const next = { ...state.completedTopics }
          delete next[sessionId]
          return { completedTopics: next }
        })
      },
    }),
    {
      name: 'itera-progress',
      partialize: (state) => ({ completedTopics: state.completedTopics }),
    }
  )
)

export default useProgressStore
