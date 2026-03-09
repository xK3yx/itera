import axios from 'axios'

// In production (Docker), Nginx proxies /api/ to the backend
// In dev, Vite proxies /api/ to localhost:8000
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
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
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api