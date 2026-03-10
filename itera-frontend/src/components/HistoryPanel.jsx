import { useEffect, useState } from 'react'
import useHistoryStore from '../store/historyStore'

export default function HistoryPanel({ onClose, onLoad }) {
  const { sessions, isLoading, fetchSessions, loadSession, deleteSession } = useHistoryStore()
  const [deletingId, setDeletingId] = useState(null)

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

  const handleDelete = async (e, sessionId) => {
    e.stopPropagation()
    setDeletingId(sessionId)
    await deleteSession(sessionId)
    setDeletingId(null)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black bg-opacity-40" onClick={onClose} />

      {/* Panel */}
      <div className="relative ml-auto w-full max-w-sm bg-white dark:bg-gray-800 h-full shadow-xl flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="font-semibold text-gray-800 dark:text-gray-100">Session History</h2>
          <button
            onClick={onClose}
            className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {isLoading && (
            <div className="text-center py-10 text-gray-400 dark:text-gray-500 text-sm">Loading...</div>
          )}

          {!isLoading && sessions.length === 0 && (
            <div className="text-center py-10">
              <p className="text-3xl mb-3">📭</p>
              <p className="text-gray-500 dark:text-gray-400 text-sm">No past sessions yet.</p>
              <p className="text-gray-400 dark:text-gray-500 text-xs mt-1">
                Start a conversation to generate your first roadmap!
              </p>
            </div>
          )}

          {!isLoading && sessions.length > 0 && (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div
                  key={session.session_id}
                  className="relative group border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-sm transition"
                >
                  {/* Clickable session content */}
                  <button
                    onClick={() => handleLoad(session.session_id)}
                    className="w-full text-left p-4 pr-12"
                  >
                    <p className="font-medium text-gray-800 dark:text-gray-100 text-sm truncate">
                      {session.roadmap?.goal || session.session_title || 'Learning Session'}
                    </p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 dark:text-gray-500">
                      {session.roadmap?.total_estimated_hours && (
                        <span>⏱ {session.roadmap.total_estimated_hours}h total</span>
                      )}
                      {session.roadmap?.created_at && (
                        <span>📅 {formatDate(session.roadmap.created_at)}</span>
                      )}
                    </div>
                    {session.roadmap?.skill_areas?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {session.roadmap.skill_areas.slice(0, 3).map((area, i) => (
                          <span key={i} className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded-full">
                            {area.name}
                          </span>
                        ))}
                        {session.roadmap.skill_areas.length > 3 && (
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            +{session.roadmap.skill_areas.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                  </button>

                  {/* Delete button */}
                  <button
                    onClick={(e) => handleDelete(e, session.session_id)}
                    disabled={deletingId === session.session_id}
                    className="absolute top-3 right-3 w-7 h-7 flex items-center justify-center rounded-lg text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition opacity-0 group-hover:opacity-100"
                    title="Delete session"
                  >
                    {deletingId === session.session_id ? '...' : '🗑'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}