import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api, { setAuthToken } from '../services/api'

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      register: async (email, username, password) => {
        set({ isLoading: true, error: null })
        try {
          const res = await api.post('/api/v1/auth/register', { email, username, password })
          setAuthToken(res.data.access_token)
          set({ user: res.data.user, token: res.data.access_token, isLoading: false })
          return { success: true }
        } catch (err) {
          const message = err.response?.data?.detail || 'Registration failed'
          set({ error: message, isLoading: false })
          return { success: false, error: message }
        }
      },

      login: async (email, password) => {
        set({ isLoading: true, error: null })
        try {
          const res = await api.post('/api/v1/auth/login', { email, password })
          setAuthToken(res.data.access_token)
          set({ user: res.data.user, token: res.data.access_token, isLoading: false })
          return { success: true }
        } catch (err) {
          const message = err.response?.data?.detail || 'Login failed'
          set({ error: message, isLoading: false })
          return { success: false, error: message }
        }
      },

      updateUser: (userData) => {
        set({ user: { ...get().user, ...userData } })
      },

      logout: () => {
        setAuthToken(null)
        set({ user: null, token: null, error: null })
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'itera-auth',
      partialize: (state) => ({ user: state.user, token: state.token }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) setAuthToken(state.token)
      },
    }
  )
)

export default useAuthStore
