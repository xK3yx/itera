import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import ProfileSetup from './pages/ProfileSetup'
import Recommendations from './pages/Recommendations'
import RoadmapView from './pages/RoadmapView'
import Navbar from './components/Navbar'
import useAuthStore from './store/authStore'
import './store/themeStore' // apply saved theme before first render

function ProtectedRoute({ children }) {
  const token = useAuthStore((state) => state.token)
  return token ? children : <Navigate to="/login" replace />
}

function ProfileGuard({ children }) {
  const user = useAuthStore((state) => state.user)
  if (!user?.profile_completed) return <Navigate to="/profile-setup" replace />
  return children
}

function AppLayout() {
  const token = useAuthStore((state) => state.token)
  const location = useLocation()
  const hideNavbar = ['/login', '/register'].includes(location.pathname)

  return (
    <>
      {token && !hideNavbar && <Navbar />}
      <Routes>
        <Route path="/" element={<Navigate to="/recommendations" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/profile-setup"
          element={
            <ProtectedRoute>
              <ProfileSetup />
            </ProtectedRoute>
          }
        />
        <Route
          path="/edit-profile"
          element={
            <ProtectedRoute>
              <ProfileSetup isEditing />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recommendations"
          element={
            <ProtectedRoute>
              <ProfileGuard>
                <Recommendations />
              </ProfileGuard>
            </ProtectedRoute>
          }
        />
        <Route
          path="/roadmaps/:roadmapId"
          element={
            <ProtectedRoute>
              <ProfileGuard>
                <RoadmapView />
              </ProfileGuard>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/recommendations" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  const [ready, setReady] = useState(false)
  const hydrateUser = useAuthStore((s) => s.hydrateUser)

  useEffect(() => {
    hydrateUser().finally(() => setReady(true))
  }, [hydrateUser])

  if (!ready) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
