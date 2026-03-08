import { useEffect } from 'react'
import useHistoryStore from '../store/historyStore'

export default function HistoryPanel({ onClose, onLoad }) {
  const { sessions, isLoading, fetchSessions, loadSession } = useHistoryStore()

  useEffect(() => {
    fetchSessions()
  }, [])

  const handleLoad = async (sessionId) => {
    const data = await loadSession(sessionId)
    if (data) {
      onLoad(data)
      onClose()
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-black bg-opacity-30" onClick={onClose} />
      <div className="relative ml-auto w-full max-w-sm bg-white h-full shadow-xl flex flex-col">

        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-800">Session History</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {isLoading && (
            <div className="text-center py-10 text-gray-400 text-sm">Loading...</div>
          )}

          {!isLoading && sessions.length === 0 && (
            <div className="text-center py-10">
              <p className="text-3xl mb-3">📭</p>
              <p className="text-gray-500 text-sm">No past sessions yet.</p>
              <p className="text-gray-400 text-xs mt-1">
                Start a conversation to generate your first roadmap!
              </p>
            </div>
          )}

          {!isLoading && sessions.length > 0 && (
            <div className="space-y-3">
              {sessions.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => handleLoad(session.session_id)}
                  className="w-full text-left border border-gray-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition bg-white"
                >
                  <p className="font-medium text-gray-800 text-sm truncate">
                    {session.roadmap?.goal || session.session_title || 'Learning Session'}
                  </p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                    {session.roadmap?.total_estimated_hours && (
                      <span>⏱ {session.roadmap.total_estimated_hours}h total</span>
                    )}
                    {session.roadmap?.created_at && (
                      <span>📅 {formatDate(session.roadmap.created_at)}</span>
                    )}
                  </div>
                  {session.roadmap?.skill_areas && session.roadmap.skill_areas.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {session.roadmap.skill_areas.slice(0, 3).map((area, i) => (
                        <span key={i} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                          {area.name}
                        </span>
                      ))}
                      {session.roadmap.skill_areas.length > 3 && (
                        <span className="text-xs text-gray-400">
                          +{session.roadmap.skill_areas.length - 3} more
                        </span>
                      )}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}