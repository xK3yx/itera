import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api, { setAuthToken } from '../services/api'

function extractError(err) {
  const detail = err.response?.data?.detail
  if (!detail) return err.message || 'Something went wrong'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
  }
  return String(detail)
}

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      // Verify persisted token is still valid on app load
      hydrateUser: async () => {
        const token = get().token
        if (!token) return
        try {
          const res = await api.get('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${token}` },
          })
          set({ user: res.data })
        } catch {
          // Token is invalid/expired — clear auth state
          setAuthToken(null)
          set({ user: null, token: null })
        }
      },

      register: async (email, username, password) => {
        set({ isLoading: true, error: null })
        try {
          const res = await api.post('/api/v1/auth/register', { email, username, password })
          setAuthToken(res.data.access_token)
          set({ user: res.data.user, token: res.data.access_token, isLoading: false })
          return { success: true }
        } catch (err) {
          const message = extractError(err) || 'Registration failed'
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
          const message = extractError(err) || 'Login failed'
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
