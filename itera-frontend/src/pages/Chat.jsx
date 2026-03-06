import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'
import MessageBubble from '../components/MessageBubble'
import TypingIndicator from '../components/TypingIndicator'
import RoadmapView from '../components/RoadmapView'

export default function Chat() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { sessionId, messages, roadmap, isTyping, startSession, sendMessage, clearSession } = useChatStore()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    if (!sessionId) {
      startSession()
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, roadmap])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || isTyping) return
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

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">I</span>
          </div>
          <span className="font-semibold text-gray-800">Itera</span>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleNewSession}
            className="text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition"
          >
            New session
          </button>
          <button
            onClick={handleLogout}
            className="text-sm text-red-500 hover:text-red-700 border border-red-200 rounded-lg px-3 py-1.5 hover:bg-red-50 transition"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl w-full mx-auto">

        {messages.length === 0 && !isTyping && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🎯</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">
              Hi{user?.username ? `, ${user.username}` : ''}! I'm your learning coach.
            </h2>
            <p className="text-gray-500 text-sm max-w-md mx-auto">
              Tell me what you want to learn and what you already know.
              I'll build you a personalized roadmap with courses.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isTyping && <TypingIndicator />}

        {/* Roadmap renders here after AI generates it */}
        {roadmap && <RoadmapView roadmap={roadmap} />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-end space-x-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Tell me what you want to learn..."
            rows={1}
            className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 max-h-32"
            style={{ minHeight: '44px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="bg-blue-600 hover:bg-blue-700 text-white rounded-xl px-5 py-3 text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 mt-2">Press Enter to send</p>
      </div>

    </div>
  )
}