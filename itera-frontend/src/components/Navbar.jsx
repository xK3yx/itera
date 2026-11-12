import { Link, NavLink, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import useThemeStore from '../store/themeStore'

const THEME_ORDER = ['light', 'dark', 'system']
const THEME_LABEL = { light: '☀️ Light', dark: '🌙 Dark', system: '💻 Auto' }

const linkClass = ({ isActive }) =>
  `text-sm px-3 py-1.5 rounded-lg transition ${
    isActive
      ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
      : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
  }`

const buttonClass =
  'text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition'

export default function Navbar() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const theme = useThemeStore((s) => s.theme)
  const setTheme = useThemeStore((s) => s.setTheme)
  const navigate = useNavigate()

  const cycleTheme = () => {
    const next = THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length]
    setTheme(next)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center justify-between gap-3 transition-colors">
      <Link to="/recommendations" className="flex items-center gap-2.5 shrink-0">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-sm">
          <span className="text-white text-sm font-bold">I</span>
        </div>
        <span className="font-semibold text-gray-900 dark:text-white tracking-tight">Itera</span>
      </Link>

      {user?.profile_completed && (
        <nav className="hidden sm:flex items-center gap-1">
          <NavLink to="/recommendations" className={linkClass}>
            Roadmaps
          </NavLink>
          <NavLink to="/edit-profile" className={linkClass}>
            Profile
          </NavLink>
        </nav>
      )}

      <div className="flex items-center gap-1.5">
        {user?.username && (
          <span className="hidden md:inline text-xs text-gray-500 dark:text-gray-400 mr-1">
            {user.username}
          </span>
        )}
        <button onClick={cycleTheme} aria-label="Toggle theme" className={buttonClass}>
          {THEME_LABEL[theme] ?? THEME_LABEL.system}
        </button>
        <button
          onClick={handleLogout}
          aria-label="Log out"
          className="text-xs text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 border border-red-200 dark:border-red-800 rounded-lg px-2.5 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
        >
          Log out
        </button>
      </div>
    </header>
  )
}
