import { useState, useEffect } from 'react'
import useScheduleStore from '../store/scheduleStore'

const ALL_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const DAY_SHORT = { Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed', Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun' }

export default function StudyCoach({ sessionId }) {
  const { schedule, todayPlan, isLoading, isGenerating, generateSchedule, fetchSchedule } = useScheduleStore()

  const [expanded, setExpanded] = useState(false)
  const [showSetup, setShowSetup] = useState(false)
  const [showFullSchedule, setShowFullSchedule] = useState(false)
  const [dailyHours, setDailyHours] = useState(2)
  const [studyDays, setStudyDays] = useState(['Monday', 'Wednesday', 'Friday'])
  const [successMsg, setSuccessMsg] = useState(null)

  // Fetch existing schedule when this component mounts
  useEffect(() => {
    if (sessionId) fetchSchedule(sessionId)
  }, [sessionId])

  const toggleDay = (day) => {
    setStudyDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    )
  }

  const handleGenerate = async () => {
    if (studyDays.length === 0) return
    const result = await generateSchedule(sessionId, dailyHours, studyDays)
    if (result.success) {
      setShowSetup(false)
      setSuccessMsg('✅ Study schedule generated!')
      setTimeout(() => setSuccessMsg(null), 3000)
    }
  }

  // ── Collapsed pill ────────────────────────────────────────────────────────
  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="mt-4 w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl hover:border-blue-300 dark:hover:border-blue-600 transition shadow-sm text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📅</span>
          <div>
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">Daily Study Coach</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {schedule ? 'View today\'s study plan' : 'Set up your study schedule'}
            </p>
          </div>
        </div>
        <span className="text-gray-400 text-xs">▼</span>
      </button>
    )
  }

  // ── Expanded card ─────────────────────────────────────────────────────────
  return (
    <div className="mt-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(false)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📅</span>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">Daily Study Coach</p>
        </div>
        <span className="text-gray-400 text-xs">▲</span>
      </button>

      <div className="px-5 pb-5 border-t border-gray-100 dark:border-gray-700">
        {successMsg && (
          <p className="mt-3 text-xs px-3 py-2 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-800">
            {successMsg}
          </p>
        )}

        {isLoading ? (
          <p className="mt-4 text-sm text-gray-400 dark:text-gray-500 text-center">Loading schedule...</p>
        ) : !schedule || showSetup ? (
          // ── Setup Form ───────────────────────────────────────────────────
          <div className="mt-4 space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Tell me when you study and I'll build a day-by-day plan from your roadmap.
            </p>

            {/* Daily hours */}
            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-2">
                Daily study time: <span className="text-blue-600 dark:text-blue-400 font-bold">{dailyHours}h</span>
              </label>
              <input
                type="range"
                min={0.5}
                max={8}
                step={0.5}
                value={dailyHours}
                onChange={(e) => setDailyHours(parseFloat(e.target.value))}
                className="w-full accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>30 min</span>
                <span>8 h</span>
              </div>
            </div>

            {/* Study days */}
            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-2">
                Study days
              </label>
              <div className="flex flex-wrap gap-2">
                {ALL_DAYS.map((day) => (
                  <button
                    key={day}
                    onClick={() => toggleDay(day)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      studyDays.includes(day)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {DAY_SHORT[day]}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleGenerate}
                disabled={isGenerating || studyDays.length === 0}
                className="flex-1 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGenerating ? '⏳ Generating...' : '✨ Generate my schedule'}
              </button>
              {schedule && (
                <button
                  onClick={() => setShowSetup(false)}
                  className="px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-600 text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        ) : (
          // ── Schedule View ────────────────────────────────────────────────
          <div className="mt-4 space-y-4">
            {/* Today's Plan */}
            {todayPlan ? (
              todayPlan.is_study_day ? (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-semibold text-blue-800 dark:text-blue-200">
                      📖 Today's Plan — Day {todayPlan.day_number}
                    </p>
                    <span className="text-xs bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200 px-2 py-1 rounded-lg font-medium">
                      {todayPlan.plan?.total_hours ?? schedule.daily_hours}h
                    </span>
                  </div>
                  {todayPlan.plan?.summary && (
                    <p className="text-xs text-blue-700 dark:text-blue-300 mb-3 italic">{todayPlan.plan.summary}</p>
                  )}
                  <div className="space-y-2">
                    {(todayPlan.plan?.topics || []).map((t, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <span className="text-blue-400 dark:text-blue-500 mt-0.5 shrink-0">•</span>
                        <div>
                          <span className="font-medium text-gray-800 dark:text-gray-100">{t.topic}</span>
                          <span className="text-gray-500 dark:text-gray-400"> — {t.skill_area}</span>
                          {t.activity && <p className="text-gray-500 dark:text-gray-400 mt-0.5">{t.activity}</p>}
                        </div>
                        <span className="ml-auto shrink-0 text-blue-600 dark:text-blue-400 font-medium">{t.hours}h</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600 rounded-xl p-4 text-center">
                  <p className="text-2xl mb-2">😌</p>
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Rest day today</p>
                  {todayPlan.next_study_day && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Next study day: <span className="font-medium">{todayPlan.next_study_day}</span>
                    </p>
                  )}
                </div>
              )
            ) : null}

            {/* Schedule summary pills */}
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
              <span>⏱ {schedule.daily_hours}h/day</span>
              <span>•</span>
              <span>{schedule.study_days?.join(', ')}</span>
              <span>•</span>
              <span>{schedule.schedule?.length ?? 0} study days total</span>
            </div>

            {/* Full schedule toggle */}
            <button
              onClick={() => setShowFullSchedule((v) => !v)}
              className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
            >
              {showFullSchedule ? '▲ Hide full schedule' : '▼ View full schedule'}
            </button>

            {showFullSchedule && (
              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {(schedule.schedule || []).map((day) => (
                  <div key={day.day_number} className="border border-gray-100 dark:border-gray-700 rounded-xl p-3">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">Day {day.day_number}</p>
                      <span className="text-xs text-gray-400 dark:text-gray-500">{day.total_hours}h</span>
                    </div>
                    {day.summary && <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 italic">{day.summary}</p>}
                    <div className="space-y-0.5">
                      {(day.topics || []).map((t, i) => (
                        <p key={i} className="text-xs text-gray-600 dark:text-gray-300">
                          • <span className="font-medium">{t.topic}</span> ({t.hours}h)
                        </p>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Regenerate link */}
            <button
              onClick={() => setShowSetup(true)}
              className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 underline"
            >
              Regenerate schedule with different settings
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
