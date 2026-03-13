import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

const useScheduleStore = create(
  persist(
    (set, get) => ({
      schedule: null,    // ScheduleResponse from backend
      todayPlan: null,   // { is_study_day, day_number, plan }
      isLoading: false,
      isGenerating: false,
      error: null,

      fetchSchedule: async (sessionId) => {
        set({ isLoading: true, error: null })
        try {
          const res = await api.get(`/schedule/${sessionId}`)
          set({ schedule: res.data, isLoading: false })
          // Fetch today's plan alongside
          get()._fetchTodayPlan(sessionId)
        } catch (err) {
          if (err.response?.status === 404) {
            // No schedule yet — not an error
            set({ schedule: null, todayPlan: null, isLoading: false })
          } else {
            set({ error: 'Failed to load schedule', isLoading: false })
          }
        }
      },

      _fetchTodayPlan: async (sessionId) => {
        try {
          const res = await api.get(`/schedule/${sessionId}/today`)
          set({ todayPlan: res.data })
        } catch {
          set({ todayPlan: null })
        }
      },

      generateSchedule: async (sessionId, dailyHours, studyDays) => {
        set({ isGenerating: true, error: null })
        try {
          const res = await api.post('/schedule/generate', {
            session_id: sessionId,
            daily_hours: dailyHours,
            study_days: studyDays,
          })
          set({ schedule: res.data, isGenerating: false })
          get()._fetchTodayPlan(sessionId)
          return { success: true }
        } catch {
          set({ error: 'Failed to generate schedule', isGenerating: false })
          return { success: false }
        }
      },

      clearSchedule: () => set({ schedule: null, todayPlan: null }),
    }),
    {
      name: 'itera-schedule',
      partialize: (state) => ({ schedule: state.schedule }),
    }
  )
)

export default useScheduleStore
