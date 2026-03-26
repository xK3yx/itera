import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { generateRoadmap, listGeneratedRoadmaps, deleteGeneratedRoadmap } from '../services/api'
import useAuthStore from '../store/authStore'

const LOADING_STAGES = [
  { after: 0,   msg: 'Analyzing your profile...' },
  { after: 10,  msg: 'Generating learning path structure...' },
  { after: 30,  msg: 'Searching for courses on YouTube, Coursera, Udemy...' },
  { after: 60,  msg: 'Building knowledge base for progress tracking...' },
  { after: 90,  msg: 'Almost done, finalizing your roadmap...' },
]

function useLoadingMessage(active) {
  const [msg, setMsg] = useState(LOADING_STAGES[0].msg)
  const timerRef = useRef(null)
  const startRef = useRef(null)

  useEffect(() => {
    if (!active) { setMsg(LOADING_STAGES[0].msg); return }
    startRef.current = Date.now()
    const tick = () => {
      const elapsed = (Date.now() - startRef.current) / 1000
      let current = LOADING_STAGES[0].msg
      for (const stage of LOADING_STAGES) {
        if (elapsed >= stage.after) current = stage.msg
      }
      setMsg(current)
    }
    timerRef.current = setInterval(tick, 1000)
    return () => clearInterval(timerRef.current)
  }, [active])

  return msg
}

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
  const loadingMsg = useLoadingMessage(generating)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    loadHistory()
  }, [])

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
    try {
      const payload = {
        target_role: form.target_role.trim(),
        learning_goal: form.learning_goal.trim(),
        interests: form.interests.trim() || null,
        hours_per_week: form.hours_per_week ? parseFloat(form.hours_per_week) : null,
        include_paid: form.include_paid,
      }
      const res = await generateRoadmap(payload)
      const roadmap = res.data.data
      navigate(`/roadmaps/${roadmap.id}`)
    } catch (err) {
      setGenError(err.response?.data?.detail || 'Roadmap generation failed. Please try again.')
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
      {/* History sidebar */}
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
                    {rm.total_estimated_hours ? `${Math.round(rm.total_estimated_hours)}h` : ''}{' '}
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

      {/* Main content */}
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
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Target Role <span className="text-red-500">*</span>
                </label>
                <input
                  name="target_role" value={form.target_role} onChange={handleChange}
                  placeholder="e.g. Backend Developer, ML Engineer, DevOps Architect"
                  className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Learning Goal <span className="text-red-500">*</span>
                </label>
                <textarea
                  name="learning_goal" value={form.learning_goal} onChange={handleChange}
                  rows={3} placeholder="e.g. I want to transition from frontend to backend, learn system design, and build scalable APIs..."
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
                type="submit" disabled={!canSubmit || generating}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg py-3 text-sm transition flex items-center justify-center gap-2"
              >
                {generating ? (
                  <>
                    <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    {loadingMsg}
                  </>
                ) : (
                  'Generate Roadmap'
                )}
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
    </div>
  )
}
