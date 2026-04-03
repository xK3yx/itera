import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getGeneratedRoadmap,
  deleteGeneratedRoadmap,
  enrollInRoadmap,
  getEnrollment,
  logProgress,
} from '../services/api'

// Handles both old flat-number format and v3.1 {free, paid} format.
// For old data, paid path is estimated at 70% of free hours (paid resources are more concise).
function parseHours(val) {
  if (val == null) return null
  if (typeof val === 'object' && 'free' in val) return { free: val.free, paid: val.paid }
  const h = parseFloat(val)
  if (isNaN(h) || h <= 0) return null
  return { free: h, paid: Math.round(h * 0.7 * 10) / 10 }
}

const PHASE_COLORS = ['blue', 'purple', 'green', 'orange', 'pink']

const phaseStyle = (idx) => {
  const colors = [
    'border-blue-500 bg-blue-50 dark:bg-blue-900/10',
    'border-purple-500 bg-purple-50 dark:bg-purple-900/10',
    'border-green-500 bg-green-50 dark:bg-green-900/10',
    'border-orange-500 bg-orange-50 dark:bg-orange-900/10',
    'border-pink-500 bg-pink-50 dark:bg-pink-900/10',
  ]
  return colors[idx % colors.length]
}

const phaseNumStyle = (idx) => {
  const colors = [
    'bg-blue-600', 'bg-purple-600', 'bg-green-600', 'bg-orange-500', 'bg-pink-600',
  ]
  return colors[idx % colors.length]
}

const platformStyle = (platform) => {
  const map = {
    YouTube: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    Coursera: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    Udemy: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    freeCodeCamp: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  }
  return map[platform] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

function ResourceChip({ r }) {
  const formatLabel = r.format === 'playlist' ? 'Playlist' : r.format === 'video' ? 'Video' : null
  return (
    <a
      href={r.url} target="_blank" rel="noopener noreferrer"
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium hover:opacity-80 transition-opacity ${platformStyle(r.platform)}`}
    >
      <span className="font-semibold">{r.platform}</span>
      {formatLabel && <span className="opacity-60">({formatLabel})</span>}
      <span className="opacity-80">· {r.title.slice(0, 50)}{r.title.length > 50 ? '...' : ''}</span>
    </a>
  )
}

function LogProgressModal({ topicId, topicTitle, roadmapId, onClose, onAccepted }) {
  const [text, setText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setResult(null)
    try {
      const res = await logProgress(roadmapId, topicId, text)
      setResult(res.data)
      if (res.data.accepted) {
        setTimeout(() => {
          onAccepted(res.data)
          onClose()
        }, 1500)
      }
    } catch (err) {
      setResult({ accepted: false, reason: err.response?.data?.detail || 'Submission failed.' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Log Progress</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-2xl leading-none">×</button>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Topic: <strong className="text-gray-700 dark:text-gray-300">{topicTitle}</strong>
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={text} onChange={(e) => setText(e.target.value)}
            rows={5} minLength={20} maxLength={2000} required
            placeholder="Describe specifically what you learned: concepts, tools, techniques, how you applied them..."
            className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="flex items-center justify-between">
            <span className={`text-xs ${text.length < 20 ? 'text-red-400' : 'text-gray-400'}`}>
              {text.length}/2000 (min 20)
            </span>
          </div>

          {result && (
            <div className={`rounded-lg px-4 py-3 text-sm ${result.accepted ? 'bg-green-50 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400'}`}>
              {result.accepted
                ? `✓ Accepted! Topic marked as complete.`
                : `✗ ${result.reason}`}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
              Cancel
            </button>
            <button
              type="submit" disabled={text.length < 20 || submitting}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
            >
              {submitting ? 'Submitting...' : 'Submit Log'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function TopicRow({ topic, roadmapId, completedIds, onProgressAccepted }) {
  const [open, setOpen] = useState(false)
  const [logOpen, setLogOpen] = useState(false)
  const isCompleted = completedIds.includes(topic.topic_id)

  return (
    <div className={`border rounded-lg overflow-hidden ${isCompleted ? 'border-green-200 dark:border-green-800' : 'border-gray-200 dark:border-gray-700'}`}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors ${
          isCompleted
            ? 'bg-green-50 dark:bg-green-900/10 hover:bg-green-100 dark:hover:bg-green-900/20'
            : 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750'
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          {isCompleted && (
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-green-500 flex items-center justify-center text-white text-xs">✓</span>
          )}
          <span className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">{topic.title}</span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0 ml-2">
          {topic.estimated_hours != null && (() => {
            const h = parseHours(topic.estimated_hours)
            if (!h) return null
            const avg = Math.round((h.free + h.paid) / 2 * 10) / 10
            return (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                <span className="text-gray-500 dark:text-gray-400">~{avg}h</span>
                {' · '}
                <span className="text-green-600 dark:text-green-400">{h.free}h</span>
                {' / '}
                <span className="text-amber-500 dark:text-amber-400">{h.paid}h</span>
              </span>
            )
          })()}
          <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-2 bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700 space-y-3">
          {topic.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400">{topic.description}</p>
          )}

          {topic.resources && topic.resources.length > 0 && (() => {
            const free = topic.resources.filter((r) => r.type === 'free')
            const paid = topic.resources.filter((r) => r.type === 'paid')
            return (
              <div className="space-y-3">
                {free.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-green-600 dark:text-green-400 mb-1.5 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                      Free Resources
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {free.map((r, i) => <ResourceChip key={i} r={r} />)}
                    </div>
                  </div>
                )}
                {paid.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-amber-600 dark:text-amber-400 mb-1.5 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
                      Paid Resources
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {paid.map((r, i) => <ResourceChip key={i} r={r} />)}
                    </div>
                  </div>
                )}
              </div>
            )
          })()}

          {!isCompleted && (
            <button
              onClick={() => setLogOpen(true)}
              className="mt-1 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg transition"
            >
              Log Progress
            </button>
          )}
        </div>
      )}

      {logOpen && (
        <LogProgressModal
          topicId={topic.topic_id}
          topicTitle={topic.title}
          roadmapId={roadmapId}
          onClose={() => setLogOpen(false)}
          onAccepted={onProgressAccepted}
        />
      )}
    </div>
  )
}

function AnimatedText({ text, speed = 22, onDone, className }) {
  const [displayed, setDisplayed] = useState('')

  useEffect(() => {
    if (!text) { onDone?.(); return }
    let i = 0
    const id = setInterval(() => {
      i++
      setDisplayed(text.slice(0, i))
      if (i >= text.length) { clearInterval(id); onDone?.() }
    }, speed)
    return () => clearInterval(id)
  }, [text])

  return (
    <span className={className}>
      {displayed || '\u00A0'}
      {displayed.length < (text?.length ?? 0) && (
        <span className="inline-block w-px h-[1em] bg-current ml-px align-middle animate-pulse" />
      )}
    </span>
  )
}

export default function RoadmapView() {
  const { roadmapId } = useParams()
  const navigate = useNavigate()
  const [roadmap, setRoadmap] = useState(null)
  const [enrollment, setEnrollment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [enrolling, setEnrolling] = useState(false)

  // Typewriter animation state
  const [typingPhaseIdx, setTypingPhaseIdx] = useState(0)
  const [revealedPhases, setRevealedPhases] = useState(new Set())

  const handlePhaseTypeDone = useCallback((idx) => {
    setTimeout(() => setRevealedPhases((prev) => new Set([...prev, idx])), 120)
    setTimeout(() => setTypingPhaseIdx(idx + 1), 350)
  }, [])

  const completedIds = enrollment?.completed_topic_ids || []

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rmRes, enrRes] = await Promise.all([
        getGeneratedRoadmap(roadmapId),
        getEnrollment(roadmapId),
      ])
      setRoadmap(rmRes.data.data)
      setEnrollment(enrRes.data.data)
    } catch {
      setError('Could not load roadmap.')
    } finally {
      setLoading(false)
    }
  }, [roadmapId])

  useEffect(() => { load() }, [load])

  const handleEnroll = async () => {
    setEnrolling(true)
    try {
      const res = await enrollInRoadmap(roadmapId)
      setEnrollment(res.data.data)
    } catch {
      // silent
    } finally {
      setEnrolling(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Delete this roadmap? This cannot be undone.')) return
    setDeleting(true)
    try {
      await deleteGeneratedRoadmap(roadmapId)
      navigate('/recommendations')
    } catch {
      setDeleting(false)
    }
  }

  const handleProgressAccepted = (data) => {
    setEnrollment((e) => e ? {
      ...e,
      completed_topic_ids: [...(e.completed_topic_ids || []), data.topic_id],
      total_topics: data.total_topics,
      progress_pct: Math.round(data.completed_topics / data.total_topics * 100 * 10) / 10,
    } : e)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-500 border-t-transparent mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400 text-sm">Loading roadmap...</p>
        </div>
      </div>
    )
  }

  if (error || !roadmap) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error || 'Roadmap not found.'}</p>
          <button onClick={() => navigate('/recommendations')} className="text-blue-500 hover:underline text-sm">
            ← Back to Recommendations
          </button>
        </div>
      </div>
    )
  }

  const data = roadmap.roadmap_data || {}
  const phases = data.phases || []
  const totalTopics = phases.reduce((a, p) => a + p.skill_areas.reduce((b, sa) => b + (sa.topics || []).length, 0), 0)
  const progressPct = enrollment?.progress_pct || 0
  const completedCount = completedIds.length

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/recommendations')}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors text-sm"
            >
              ← Back
            </button>
            <div>
              <h1 className="text-lg font-bold text-gray-800 dark:text-gray-100 leading-tight">{roadmap.title}</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">{roadmap.target_role}</p>
            </div>
          </div>
          <button
            onClick={handleDelete} disabled={deleting}
            className="px-3 py-1.5 text-xs text-red-500 hover:text-red-700 dark:hover:text-red-400 border border-red-200 dark:border-red-800 rounded-lg transition disabled:opacity-50"
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-6 space-y-6">
        {/* Stats + progress */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm p-5 space-y-4">
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-gray-400 dark:text-gray-500 text-xs">Phases</span>
              <p className="font-semibold text-gray-800 dark:text-gray-100">{phases.length}</p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-gray-500 text-xs">Total Topics</span>
              <p className="font-semibold text-gray-800 dark:text-gray-100">{totalTopics}</p>
            </div>
            {(() => {
              const h = parseHours(roadmap.total_estimated_hours)
              if (!h) return null
              const avg = Math.round((h.free + h.paid) / 2 * 10) / 10
              return (
                <>
                  <div>
                    <span className="text-gray-400 dark:text-gray-500 text-xs">Avg. Est.</span>
                    <p className="font-semibold text-gray-800 dark:text-gray-100">{avg}h</p>
                  </div>
                  <div>
                    <span className="text-gray-400 dark:text-gray-500 text-xs flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block" />
                      Free Path
                    </span>
                    <p className="font-semibold text-green-600 dark:text-green-400">{h.free}h</p>
                  </div>
                  <div>
                    <span className="text-gray-400 dark:text-gray-500 text-xs flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 inline-block" />
                      Paid Path
                    </span>
                    <p className="font-semibold text-amber-600 dark:text-amber-400">{h.paid}h</p>
                  </div>
                </>
              )
            })()}
            {roadmap.hours_per_week && (
              <div>
                <span className="text-gray-400 dark:text-gray-500 text-xs">Hours/Week</span>
                <p className="font-semibold text-gray-800 dark:text-gray-100">{roadmap.hours_per_week}h</p>
              </div>
            )}
          </div>

          {/* Progress bar */}
          {enrollment ? (
            <div>
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
                <span>Progress: {completedCount}/{totalTopics} topics</span>
                <span>{progressPct}%</span>
              </div>
              <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={handleEnroll} disabled={enrolling}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
            >
              {enrolling ? 'Enrolling...' : 'Start Roadmap (Enroll)'}
            </button>
          )}
        </div>

        {/* Phases — revealed one by one with typewriter on phase title */}
        {phases.map((phase, pi) => {
          if (pi > typingPhaseIdx) return null
          const revealed = revealedPhases.has(pi)
          const isTyping = pi === typingPhaseIdx
          const topicCount = phase.skill_areas?.reduce((a, sa) => a + (sa.topics || []).length, 0)
          return (
            <div key={pi} className={`rounded-2xl border-l-4 p-5 space-y-4 ${phaseStyle(pi)}`}>
              <div className="flex items-center gap-3">
                <span className={`${phaseNumStyle(pi)} text-white text-sm font-bold w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0`}>
                  {pi + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-semibold text-gray-800 dark:text-gray-100">
                    {isTyping ? (
                      <AnimatedText
                        text={phase.title}
                        speed={22}
                        onDone={() => handlePhaseTypeDone(pi)}
                      />
                    ) : phase.title}
                  </h2>
                  <p className={`text-xs text-gray-500 dark:text-gray-400 mt-0.5 transition-opacity duration-300 ${revealed ? 'opacity-100' : 'opacity-0'}`}>
                    {phase.description}
                  </p>
                </div>
                <div className={`ml-auto text-xs text-gray-400 dark:text-gray-500 flex-shrink-0 transition-opacity duration-300 ${revealed ? 'opacity-100' : 'opacity-0'}`}>
                  {topicCount} topics
                </div>
              </div>

              <div className={`space-y-4 transition-all duration-500 ${revealed ? 'opacity-100' : 'opacity-0 pointer-events-none overflow-hidden max-h-0'}`}>
                {(phase.skill_areas || []).map((sa, ai) => (
                  <div key={ai} className="space-y-2">
                    <div className="mb-2">
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{sa.title}</h3>
                      {sa.description && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">{sa.description}</p>
                      )}
                    </div>
                    <div className="space-y-1.5 pl-2">
                      {(sa.topics || []).map((topic, ti) => (
                        <TopicRow
                          key={ti}
                          topic={topic}
                          roadmapId={roadmapId}
                          completedIds={completedIds}
                          onProgressAccepted={handleProgressAccepted}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
        ))}
      </div>
    </div>
  )
}
