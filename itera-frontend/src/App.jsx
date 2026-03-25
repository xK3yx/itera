import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import ProfileSetup from './pages/ProfileSetup'
import Recommendations from './pages/Recommendations'
import RoadmapView from './pages/RoadmapView'
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

export default function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  )
}
