import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'
import useThemeStore from '../store/themeStore'
import MessageBubble from '../components/MessageBubble'
import TypingIndicator from '../components/TypingIndicator'
import RoadmapView from '../components/RoadmapView'
import HistoryPanel from '../components/HistoryPanel'

export default function Chat() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const {
    sessionId, messages, roadmap, isTyping, isLoading, error,
    startSession, sendMessage, clearSession, loadFromHistory,
  } = useChatStore()
  const { theme, setTheme } = useThemeStore()
  const [input, setInput] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (!sessionId) startSession()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, roadmap])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isTyping || isLoading) return
    setInput('')
    await sendMessage(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewSession = () => {
    clearSession()
    startSession()
  }

  const handleLogout = () => {
    logout()
    clearSession()
    navigate('/login')
  }

  const handleLoadHistory = (data) => {
    loadFromHistory(data)
  }

  const cycleTheme = () => {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system'
    setTheme(next)
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors">

      {/* Sticky Header */}
      <header className="sticky top-0 z-10 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center" aria-label="Itera">
            <span className="text-white text-sm font-bold">I</span>
          </div>
          <span className="font-semibold text-gray-800 dark:text-gray-100">Itera</span>
        </div>
        <nav className="flex items-center space-x-2" aria-label="Main navigation">
          <button
            onClick={cycleTheme}
            aria-label="Toggle theme"
            className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
          >
            {theme === 'dark' ? '🌙 Dark' : theme === 'light' ? '☀️ Light' : '💻 Auto'}
          </button>
          <button
            onClick={() => setShowHistory(true)}
            aria-label="View session history"
            className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
          >
            History
          </button>
          <button
            onClick={handleNewSession}
            aria-label="Start new session"
            className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
          >
            New session
          </button>
          <button
            onClick={handleLogout}
            aria-label="Logout"
            className="text-xs sm:text-sm text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 border border-red-200 dark:border-red-800 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
          >
            Logout
          </button>
        </nav>
      </header>

      {/* Session error banner */}
      {error && !sessionId && (
        <div className="bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800 px-4 py-3 text-center">
          <p className="text-red-600 dark:text-red-400 text-sm">
            {error}{' '}
            <button
              onClick={() => startSession()}
              className="underline font-medium hover:no-underline"
            >
              Try again
            </button>
          </p>
        </div>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl w-full mx-auto">
        {messages.length === 0 && !isTyping && !isLoading && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🎯</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">
              Hi{user?.username ? `, ${user.username}` : ''}! I'm your learning coach.
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm max-w-md mx-auto">
              Tell me what you want to learn and what you already know.
              I'll build you a personalized roadmap with courses.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isTyping && <TypingIndicator />}
        {roadmap && <RoadmapView roadmap={roadmap} />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-end space-x-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isLoading && !sessionId ? 'Starting session...' : 'Tell me what you want to learn...'}
            disabled={isLoading && !sessionId}
            rows={1}
            className="flex-1 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 max-h-32 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ minHeight: '44px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping || (isLoading && !sessionId)}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 py-3 text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-2">Press Enter to send</p>
      </div>

      {/* History panel */}
      {showHistory && (
        <HistoryPanel
          onClose={() => setShowHistory(false)}
          onLoad={handleLoadHistory}
        />
      )}
    </div>
  )
}