import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateRoadmap, listGeneratedRoadmaps, deleteGeneratedRoadmap } from '../services/api'
import useAuthStore from '../store/authStore'

// ── Role presets ───────────────────────────────────────────────────────────────
const ROLE_OPTIONS = [
  'Frontend Developer',
  'Backend Developer',
  'Full-Stack Developer',
  'Mobile Developer',
  'DevOps Engineer',
  'Cloud Engineer',
  'Data Scientist',
  'Data Engineer',
  'Data Analyst',
  'ML Engineer',
  'AI Engineer',
  'Software Engineer',
  'Site Reliability Engineer',
  'Security Engineer',
  'Cybersecurity Analyst',
  'QA Engineer',
  'Embedded Systems Engineer',
  'Game Developer',
  'Blockchain Developer',
  'iOS Developer',
  'Android Developer',
  'UI/UX Designer',
  'Product Manager',
  'Technical Writer',
  'Solutions Architect',
  'Platform Engineer',
  'Systems Administrator',
]

// ── Combobox (dropdown + typeahead) ────────────────────────────────────────────
function RoleCombobox({ label, required, value, onChange, placeholder }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef(null)

  // Close on outside click
  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = ROLE_OPTIONS.filter((r) =>
    r.toLowerCase().includes((search || value || '').toLowerCase())
  )

  const handleInputChange = (e) => {
    const v = e.target.value
    setSearch(v)
    onChange(v)
    if (!open) setOpen(true)
  }

  const handleSelect = (role) => {
    onChange(role)
    setSearch('')
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <div className="relative">
        <input
          value={value}
          onChange={handleInputChange}
          onFocus={() => setOpen(true)}
          placeholder={placeholder}
          className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
        />
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={open ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
          </svg>
        </button>
      </div>
      {open && filtered.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg py-1">
          {filtered.map((role) => (
            <li
              key={role}
              onClick={() => handleSelect(role)}
              className={`px-4 py-2 text-sm cursor-pointer transition-colors ${
                role === value
                  ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                  : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600'
              }`}
            >
              {role}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Animated generating screen ─────────────────────────────────────────────────
const GEN_STEPS = [
  { emoji: '🔍', label: 'Analyzing your profile & goals' },
  { emoji: '🗺️', label: 'Designing your learning path' },
  { emoji: '📚', label: 'Generating topics & resources' },
  { emoji: '⏱️', label: 'Calculating time estimates' },
  { emoji: '✨', label: 'Finalizing your personalized roadmap' },
]
const STEP_AT = [0, 10, 25, 50, 70]

function GeneratingScreen({ elapsed }) {
  const currentStep = STEP_AT.reduce((acc, t, i) => (elapsed >= t ? i : acc), 0)
  const progress = Math.min(96, (elapsed / 90) * 100)
  const fmt = (s) => (s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`)

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/20">
            <span className="text-3xl animate-pulse">🗺️</span>
          </div>
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">
            Building your roadmap…
          </h2>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            {fmt(elapsed)} elapsed · typically 1–2 minutes
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm mb-5">
          {GEN_STEPS.map((step, i) => {
            const done = i < currentStep
            const active = i === currentStep
            return (
              <div
                key={i}
                className={[
                  'flex items-center gap-3 px-5 py-3.5 transition-colors duration-500',
                  i > 0 ? 'border-t border-gray-100 dark:border-gray-700' : '',
                  active ? 'bg-blue-50 dark:bg-blue-900/20' : '',
                ].join(' ')}
              >
                <span className={[
                  'text-base shrink-0 transition-opacity duration-500',
                  done ? 'opacity-60' : active ? '' : 'opacity-20',
                ].join(' ')}>
                  {done ? '✅' : step.emoji}
                </span>
                <span className={[
                  'text-sm flex-1 transition-all duration-500',
                  active
                    ? 'text-blue-700 dark:text-blue-300 font-medium'
                    : done
                    ? 'text-gray-400 dark:text-gray-500 line-through'
                    : 'text-gray-300 dark:text-gray-600',
                ].join(' ')}>
                  {step.label}
                </span>
                {active && (
                  <div className="flex gap-1 shrink-0">
                    {[0, 1, 2].map((j) => (
                      <div
                        key={j}
                        className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"
                        style={{ animationDelay: `${j * 150}ms` }}
                      />
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-1000"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="text-center text-xs text-gray-400 dark:text-gray-500">
          Don't close this tab — we'll take you straight to your roadmap when it's ready
        </p>
      </div>
    </div>
  )
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function formatHours(h) {
  if (h == null) return ''
  if (typeof h === 'object' && 'free' in h) {
    const avg = Math.round((h.free + h.paid) / 2 * 10) / 10
    return `~${avg}h`
  }
  return `~${Math.round(h)}h`
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function Recommendations() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const [form, setForm] = useState({
    target_role: '',
    learning_goal: '',
    interests: '',
    hours_per_week: '',
    include_paid: true,
  })
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef(null)

  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => { loadHistory() }, [])

  useEffect(() => {
    if (generating) {
      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [generating])

  const loadHistory = async () => {
    setHistoryLoading(true)
    try {
      const res = await listGeneratedRoadmaps()
      setHistory(res.data.data || [])
    } catch {
      // silent
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const handleGenerate = async (e) => {
    e.preventDefault()
    setGenError('')
    setGenerating(true)
    const prevCount = history.length

    try {
      const payload = {
        target_role: form.target_role.trim(),
        learning_goal: form.learning_goal.trim(),
        interests: form.interests.trim() || null,
        hours_per_week: form.hours_per_week ? parseFloat(form.hours_per_week) : null,
        include_paid: form.include_paid,
      }
      const res = await generateRoadmap(payload)
      navigate(`/roadmaps/${res.data.data.id}`)
    } catch (err) {
      // Backend may still be generating. Poll for up to 5 minutes (60 × 5s).
      let found = false
      for (let attempt = 0; attempt < 60 && !found; attempt++) {
        await new Promise((r) => setTimeout(r, 5000))
        try {
          const listRes = await listGeneratedRoadmaps()
          const roadmaps = listRes.data.data || []
          if (roadmaps.length > prevCount) {
            navigate(`/roadmaps/${roadmaps[0].id}`)
            found = true
            return
          }
        } catch { /* keep polling */ }
      }
      if (!found) {
        setGenError(err.response?.data?.detail || 'Roadmap generation failed. Please try again.')
      }
    } finally {
      setGenerating(false)
    }
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Delete this roadmap?')) return
    setDeletingId(id)
    try {
      await deleteGeneratedRoadmap(id)
      setHistory((h) => h.filter((r) => r.id !== id))
    } catch {
      // silent
    } finally {
      setDeletingId(null)
    }
  }

  const canSubmit = form.target_role.trim().length >= 2 && form.learning_goal.trim().length >= 10

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* ── History sidebar ── */}
      <aside className="w-72 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">My Roadmaps</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {historyLoading ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 p-2">Loading...</p>
          ) : history.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 p-2">No roadmaps yet. Generate one!</p>
          ) : (
            history.map((rm) => (
              <div
                key={rm.id}
                onClick={() => navigate(`/roadmaps/${rm.id}`)}
                className="group flex items-start justify-between p-3 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{rm.title}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{rm.target_role}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                    {formatHours(rm.total_estimated_hours)}{' '}
                    · {new Date(rm.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => handleDelete(rm.id, e)}
                  disabled={deletingId === rm.id}
                  className="ml-2 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-opacity text-lg leading-none flex-shrink-0"
                  title="Delete"
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* ── Main content: generating screen OR form ── */}
      {generating ? (
        <GeneratingScreen elapsed={elapsed} />
      ) : (
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-2xl mx-auto">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                Generate a Learning Roadmap
              </h1>
              <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
                Tell us where you want to go and we'll build you a personalized path.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-6">
              <form onSubmit={handleGenerate} className="space-y-5">
                <RoleCombobox
                  label="Target Role"
                  required
                  value={form.target_role}
                  onChange={(v) => setForm((f) => ({ ...f, target_role: v }))}
                  placeholder="Select or type a role..."
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Learning Goal <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    name="learning_goal" value={form.learning_goal} onChange={handleChange}
                    rows={3}
                    placeholder="e.g. I want to transition from frontend to backend, learn system design, and build scalable APIs..."
                    className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Interests <span className="text-gray-400 font-normal">(optional)</span>
                  </label>
                  <input
                    name="interests" value={form.interests} onChange={handleChange}
                    placeholder="e.g. distributed systems, open source, gaming, fintech..."
                    className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="flex items-center gap-6">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Hours per Week <span className="text-gray-400 font-normal">(optional)</span>
                    </label>
                    <input
                      name="hours_per_week" type="number" min="1" max="168"
                      value={form.hours_per_week} onChange={handleChange}
                      placeholder="e.g. 10"
                      className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div className="flex items-center gap-2 pt-5">
                    <input
                      id="include_paid" name="include_paid" type="checkbox"
                      checked={form.include_paid} onChange={handleChange}
                      className="w-4 h-4 rounded text-blue-600"
                    />
                    <label htmlFor="include_paid" className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                      Include paid resources
                    </label>
                  </div>
                </div>

                {genError && (
                  <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm rounded-lg px-4 py-3">
                    {genError}
                  </div>
                )}

                <button
                  type="submit" disabled={!canSubmit}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg py-3 text-sm transition"
                >
                  Generate Roadmap
                </button>
              </form>
            </div>

            {/* Profile summary */}
            <div className="mt-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4 text-sm text-blue-700 dark:text-blue-300">
              Generating for: <strong>{user?.username}</strong> · {user?.primary_domain} · {user?.experience_years}y exp
              · Tech: {(user?.tech_stack || []).join(', ') || 'none'}
            </div>
          </div>
        </main>
      )}
    </div>
  )
}
