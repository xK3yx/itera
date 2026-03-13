import { useState, useCallback } from 'react'
import api from '../services/api'
import useProgressStore from '../store/progressStore'
import useChatStore from '../store/chatStore'

// Module-level cache: explanations persist for the session without a store
const explanationCache = new Map()

function getSearchUrl(platform, title) {
  const query = encodeURIComponent(title)
  const p = platform?.toLowerCase() || ''
  if (p.includes('coursera')) return `https://www.coursera.org/search?query=${query}`
  if (p.includes('udemy')) return `https://www.udemy.com/courses/search/?q=${query}`
  if (p.includes('youtube')) return `https://www.youtube.com/results?search_query=${query}`
  if (p.includes('freecodecamp')) return `https://www.freecodecamp.org/news/search/?query=${query}`
  if (p.includes('pluralsight')) return `https://www.pluralsight.com/search?q=${query}`
  if (p.includes('edx')) return `https://www.edx.org/search?q=${query}`
  if (p.includes('linkedin')) return `https://www.linkedin.com/learning/search?keywords=${query}`
  return `https://www.google.com/search?q=${query}+${encodeURIComponent(platform || 'course')}`
}

function CourseCard({ course }) {
  const url = getSearchUrl(course.platform, course.title)
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="block border border-gray-200 dark:border-gray-600 rounded-xl p-4 hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-sm transition bg-white dark:bg-gray-800"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-100 leading-snug">{course.title}</p>
          {course.why_recommended && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{course.why_recommended}</p>
          )}
        </div>
        <span className="shrink-0 text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium px-2 py-1 rounded-lg">
          {course.platform}
        </span>
      </div>
      <div className="flex items-center gap-3 mt-3 text-xs text-gray-400 dark:text-gray-500">
        {course.duration && <span>⏱ {course.duration}</span>}
        {course.level && <span>📊 {course.level}</span>}
        <span className="ml-auto text-blue-500 dark:text-blue-400 font-medium">Search course →</span>
      </div>
    </a>
  )
}

// ─── Feature 1: Explain Button ────────────────────────────────────────────────
function ExplainButton({ topicKey, topic, goal }) {
  const [loading, setLoading] = useState(false)
  const [explanation, setExplanation] = useState(() => explanationCache.get(topicKey) || null)
  const [open, setOpen] = useState(false)

  const handleExplain = useCallback(async (e) => {
    e.stopPropagation()
    if (explanation) { setOpen(o => !o); return }
    setLoading(true)
    try {
      const res = await api.post('/explain/topic', {
        topic_name: topic.name,
        topic_description: topic.description || '',
        why_relevant: topic.why_relevant || '',
        goal,
      })
      const text = res.data.explanation
      explanationCache.set(topicKey, text)
      setExplanation(text)
      setOpen(true)
    } catch {
      const fallback = 'Failed to load explanation. Please try again.'
      setExplanation(fallback)
      setOpen(true)
    } finally {
      setLoading(false)
    }
  }, [explanation, topicKey, topic, goal])

  return (
    <div>
      <button
        onClick={handleExplain}
        disabled={loading}
        className="text-xs font-medium px-2.5 py-1 rounded-lg bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/50 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? '⏳ Explaining...' : open ? '✕ Hide explanation' : '💡 Explain this'}
      </button>
      {open && explanation && (
        <div className="mt-3 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-xl text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
          {explanation}
        </div>
      )}
    </div>
  )
}

// ─── Feature 2: Topic Item with Checkbox ──────────────────────────────────────
function TopicItem({ topic, sessionId, areaName, goal }) {
  const [open, setOpen] = useState(false)
  const topicKey = `${areaName}::${topic.name}`
  const { isCompleted, toggleTopic } = useProgressStore()
  const completed = sessionId ? isCompleted(sessionId, topicKey) : false

  const handleCheck = useCallback((e) => {
    e.stopPropagation()
    if (sessionId) toggleTopic(sessionId, topicKey)
  }, [sessionId, topicKey, toggleTopic])

  return (
    <div className={`border rounded-xl overflow-hidden transition-colors ${
      completed
        ? 'border-green-300 dark:border-green-700'
        : 'border-gray-200 dark:border-gray-600'
    }`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left"
      >
        <div className="flex items-center gap-3">
          {/* Feature 2: Completion checkbox */}
          <div
            role="checkbox"
            aria-checked={completed}
            onClick={handleCheck}
            className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 cursor-pointer transition-colors ${
              completed
                ? 'bg-green-500 border-green-500'
                : 'border-gray-300 dark:border-gray-500 hover:border-green-400'
            }`}
          >
            {completed && <span className="text-white text-xs font-bold leading-none">✓</span>}
          </div>
          <span className={`text-sm font-medium transition-colors ${
            completed
              ? 'line-through text-gray-400 dark:text-gray-500'
              : 'text-gray-800 dark:text-gray-100'
          }`}>
            {topic.name}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-400 dark:text-gray-500">{topic.estimated_hours}h</span>
          <span className="text-gray-400 dark:text-gray-500 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-700 space-y-3 pt-3">
          {topic.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400">{topic.description}</p>
          )}
          {topic.why_relevant && (
            <p className="text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg px-3 py-2">
              💡 {topic.why_relevant}
            </p>
          )}

          {/* Feature 1: Explain button */}
          {goal && <ExplainButton topicKey={topicKey} topic={topic} goal={goal} />}

          {topic.courses?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                Recommended Courses
              </p>
              {topic.courses.map((course, i) => (
                <CourseCard key={i} course={course} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Feature 2: Skill Area with Progress Bar ──────────────────────────────────
function SkillArea({ area, index, sessionId, goal }) {
  const [open, setOpen] = useState(true)
  const { isCompleted } = useProgressStore()

  const topics = area.topics || []
  const completedCount = sessionId
    ? topics.filter(t => isCompleted(sessionId, `${area.name}::${t.name}`)).length
    : 0
  const pct = topics.length > 0 ? Math.round((completedCount / topics.length) * 100) : 0

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden shadow-sm">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-white text-sm font-bold shrink-0 ${
            pct === 100 ? 'bg-green-500' : 'bg-blue-600'
          }`}>
            {pct === 100 ? '✓' : index + 1}
          </div>
          <div>
            <p className="font-semibold text-gray-800 dark:text-gray-100">{area.name}</p>
            {area.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{area.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-3 py-1 rounded-full font-medium">
            {area.estimated_hours}h
          </span>
          <span className="text-gray-400 dark:text-gray-500 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Feature 2: Per-area progress bar */}
      {topics.length > 0 && (
        <div className="px-5 py-2 bg-white dark:bg-gray-800 border-t border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0">
              {completedCount}/{topics.length}
            </span>
          </div>
        </div>
      )}

      {open && topics.length > 0 && (
        <div className="px-5 pb-5 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-700 space-y-2 pt-3">
          {topics.map((topic, i) => (
            <TopicItem key={i} topic={topic} sessionId={sessionId} areaName={area.name} goal={goal} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Main RoadmapView ─────────────────────────────────────────────────────────
export default function RoadmapView({ roadmap, sessionId }) {
  const { updateRoadmap } = useChatStore()
  const { completedTopics, clearProgress } = useProgressStore()
  const [adapting, setAdapting] = useState(false)
  const [adaptMsg, setAdaptMsg] = useState(null)

  if (!roadmap) return null

  const totalHours = roadmap.total_estimated_hours
  const weeklyHours = roadmap.weekly_hours ?? 10
  const estimatedWeeks = roadmap.estimated_weeks ?? (totalHours ? Math.ceil(totalHours / weeklyHours) : null)

  // Feature 2: overall completion %
  const allTopicKeys = (roadmap.skill_areas || []).flatMap(a =>
    (a.topics || []).map(t => `${a.name}::${t.name}`)
  )
  const sessionDone = sessionId ? (completedTopics[sessionId] || []) : []
  const doneCount = allTopicKeys.filter(k => sessionDone.includes(k)).length
  const overallPct = allTopicKeys.length > 0 ? Math.round((doneCount / allTopicKeys.length) * 100) : 0

  // Feature 4: Adapt roadmap handler
  const handleAdapt = async () => {
    if (!sessionId || sessionDone.length === 0) return
    setAdapting(true)
    setAdaptMsg(null)
    try {
      const res = await api.post(`/roadmap/${sessionId}/adapt`)
      const newRoadmap = res.data.roadmap
      if (newRoadmap) {
        updateRoadmap(newRoadmap)
        clearProgress(sessionId)
        setAdaptMsg('✅ Roadmap updated — completed topics removed and hours recalculated.')
      }
    } catch {
      setAdaptMsg('❌ Failed to update roadmap. Please try again.')
    } finally {
      setAdapting(false)
    }
  }

  return (
    <div className="mt-6 bg-gray-50 dark:bg-gray-900/50 rounded-2xl p-5 border border-gray-200 dark:border-gray-700">
      {/* Header row */}
      <div className="flex items-start justify-between mb-4 gap-3 flex-wrap">
        <div>
          <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">🗺 Your Learning Roadmap</h2>
          {roadmap.goal && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{roadmap.goal}</p>
          )}
        </div>
        {/* Feature 4: Update roadmap button — only visible when topics are completed */}
        {sessionId && sessionDone.length > 0 && (
          <button
            onClick={handleAdapt}
            disabled={adapting}
            className="shrink-0 text-xs font-medium px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {adapting ? '⏳ Updating...' : '🔄 Update my roadmap'}
          </button>
        )}
      </div>

      {adaptMsg && (
        <p className="mb-4 text-xs px-3 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
          {adaptMsg}
        </p>
      )}

      {/* Feature 2: Overall progress bar */}
      {allTopicKeys.length > 0 && (
        <div className="mb-5 bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">Overall Progress</span>
            <span className="text-sm font-bold text-blue-600 dark:text-blue-400">{overallPct}%</span>
          </div>
          <div className="h-3 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-green-500 rounded-full transition-all duration-500"
              style={{ width: `${overallPct}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1.5">
            {doneCount} of {allTopicKeys.length} topics completed
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalHours ?? 'N/A'}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Total hours</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{weeklyHours}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Hours/week</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{estimatedWeeks ?? 'N/A'}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Weeks</p>
        </div>
      </div>

      {/* Skill areas */}
      <div className="space-y-3">
        {roadmap.skill_areas?.map((area, i) => (
          <SkillArea key={i} area={area} index={i} sessionId={sessionId} goal={roadmap.goal} />
        ))}
      </div>
    </div>
  )
}
