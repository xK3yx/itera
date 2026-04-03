import axios from 'axios'

const api = axios.create({
  baseURL: '/',
  timeout: 120000, // 2 min for LLM generation
})

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      // Don't redirect for auth endpoints — let the form handle & display the error
      const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register')
      if (!isAuthEndpoint) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

const authHeaders = () => ({
  Authorization: api.defaults.headers.common['Authorization'],
})

// --- Auth ---
export const loginUser = (email, password) =>
  api.post('/api/v1/auth/login', { email, password })

export const registerUser = (email, username, password) =>
  api.post('/api/v1/auth/register', { email, username, password })

export const getMe = () =>
  api.get('/api/v1/auth/me', { headers: authHeaders() })

// --- Profile ---
export const updateProfile = (payload) =>
  api.put('/api/v1/users/me', payload, { headers: authHeaders() })

// --- v3 Roadmaps ---
export const generateRoadmap = (payload) =>
  api.post('/api/v3/roadmaps/generate', payload, { headers: authHeaders(), timeout: 600000 })

export const listGeneratedRoadmaps = () =>
  api.get('/api/v3/roadmaps/', { headers: authHeaders() })

export const getGeneratedRoadmap = (roadmapId) =>
  api.get(`/api/v3/roadmaps/${roadmapId}`, { headers: authHeaders() })

export const deleteGeneratedRoadmap = (roadmapId) =>
  api.delete(`/api/v3/roadmaps/${roadmapId}`, { headers: authHeaders() })

// --- Enrollment & Progress ---
export const enrollInRoadmap = (roadmapId) =>
  api.post(`/api/v3/roadmaps/${roadmapId}/enroll`, {}, { headers: authHeaders() })

export const getEnrollment = (roadmapId) =>
  api.get(`/api/v3/roadmaps/${roadmapId}/enrollment`, { headers: authHeaders() })

export const logProgress = (roadmapId, topicId, logText) =>
  api.post(
    `/api/v3/roadmaps/${roadmapId}/topics/${topicId}/log`,
    { log_text: logText },
    { headers: authHeaders() }
  )

export default api
