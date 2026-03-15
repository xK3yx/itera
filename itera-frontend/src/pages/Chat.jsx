import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'
import useThemeStore from '../store/themeStore'
import MessageBubble from '../components/MessageBubble'
import TypingIndicator from '../components/TypingIndicator'
import RoadmapView from '../components/RoadmapView'
import StudyCoach from '../components/StudyCoach'
import HistoryPanel from '../components/HistoryPanel'
import { uploadFile } from '../services/api'

// ── SVG Icons ──────────────────────────────────────────────────────────────────
function PaperclipIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
    </svg>
  )
}

function MicIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  )
}

function SendIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  )
}

function SpinnerIcon({ className = 'w-5 h-5' }) {
  return (
    <svg className={`${className} animate-spin`} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  )
}

function XIcon({ className = 'w-3.5 h-3.5' }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
    </svg>
  )
}

function DocIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function Chat() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const {
    sessionId, messages, roadmap, roadmapMessageCount, isTyping, isLoading, error,
    startSession, sendMessage, clearSession, loadFromHistory,
  } = useChatStore()
  const { theme, setTheme } = useThemeStore()
  const [input, setInput] = useState('')
  const [showHistory, setShowHistory] = useState(false)

  // File upload
  const [attachedFile, setAttachedFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [fileError, setFileError] = useState(null)
  const fileInputRef = useRef(null)

  // Speech-to-text
  const [isRecording, setIsRecording] = useState(false)
  const recognitionRef = useRef(null)
  const speechSupported = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    if (!sessionId) startSession()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping, roadmap])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [input])

  // ── Handlers ─────────────────────────────────────────────────────────────────
  const handleSend = async () => {
    const text = input.trim()
    if ((!text && !attachedFile) || isTyping || isLoading) return

    let fullMessage = text
    if (attachedFile) {
      const header = `[Attached file: ${attachedFile.name}${attachedFile.truncated ? ' — truncated to 50 000 chars' : ''}]\n\n${attachedFile.content}`
      fullMessage = text ? `${header}\n\n---\n\n${text}` : header
    }

    setInput('')
    setAttachedFile(null)
    setFileError(null)
    await sendMessage(fullMessage)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // File upload
  const ACCEPTED = '.pdf,.docx,.xlsx,.xls,.txt,.md,.csv,.json'

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setFileError(null)
    if (file.size > 10 * 1024 * 1024) {
      setFileError('File too large. Maximum size is 10 MB.')
      return
    }

    setIsUploading(true)
    try {
      const res = await uploadFile(file)
      setAttachedFile({
        name: res.data.filename,
        content: res.data.content,
        size: res.data.size,
        truncated: res.data.truncated,
      })
    } catch (err) {
      setFileError(err.response?.data?.detail || 'Could not read file. Please try another.')
    } finally {
      setIsUploading(false)
    }
  }

  // Speech-to-text
  const handleMicClick = () => {
    if (!speechSupported) {
      alert('Speech recognition is not supported in your browser. Please use Chrome or Edge.')
      return
    }
    if (isRecording) {
      recognitionRef.current?.stop()
      return
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    const rec = new SR()
    rec.continuous = false
    rec.interimResults = false
    rec.lang = 'en-US'
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript
      setInput((prev) => (prev ? `${prev} ${t}` : t))
    }
    rec.onend = () => { setIsRecording(false); recognitionRef.current = null }
    rec.onerror = (e) => {
      setIsRecording(false)
      recognitionRef.current = null
      if (e.error === 'not-allowed') alert('Microphone access denied. Please allow microphone access and try again.')
    }
    recognitionRef.current = rec
    rec.start()
    setIsRecording(true)
  }

  const handleNewSession = () => { clearSession(); startSession() }
  const handleLogout = () => { logout(); clearSession(); navigate('/login') }
  const handleLoadHistory = (data) => loadFromHistory(data)
  const cycleTheme = () => {
    const next = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system'
    setTheme(next)
  }

  const canSend = (input.trim() || attachedFile) && !isTyping && !(isLoading && !sessionId)
  const disabled = isLoading && !sessionId

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors">

      {/* ── Header ── */}
      <header className="sticky top-0 z-10 bg-white/90 dark:bg-gray-900/90 backdrop-blur border-b border-gray-200 dark:border-gray-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center shadow-sm">
            <span className="text-white text-sm font-bold">I</span>
          </div>
          <span className="font-semibold text-gray-900 dark:text-white tracking-tight">Itera</span>
        </div>

        <nav className="flex items-center gap-1.5">
          <button onClick={cycleTheme} aria-label="Toggle theme"
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            {theme === 'dark' ? '🌙 Dark' : theme === 'light' ? '☀️ Light' : '💻 Auto'}
          </button>
          <button onClick={() => setShowHistory(true)} aria-label="View history"
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            History
          </button>
          <button onClick={handleNewSession} aria-label="New session"
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-lg px-2.5 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 transition">
            + New
          </button>
          <button onClick={handleLogout} aria-label="Logout"
            className="text-xs text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 border border-red-200 dark:border-red-800 rounded-lg px-2.5 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 transition">
            Logout
          </button>
        </nav>
      </header>

      {/* ── Session error banner ── */}
      {error && !sessionId && (
        <div className="bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800 px-4 py-3 text-center">
          <p className="text-red-600 dark:text-red-400 text-sm">
            {error}{' '}
            <button onClick={() => startSession()} className="underline font-medium hover:no-underline">
              Try again
            </button>
          </p>
        </div>
      )}

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 && !isTyping && !isLoading && (
            <div className="text-center py-20">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg shadow-blue-500/20">
                <span className="text-3xl">🎯</span>
              </div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
                Hi{user?.username ? `, ${user.username}` : ''}! I'm your learning coach.
              </h2>
              <p className="text-gray-500 dark:text-gray-400 text-sm max-w-sm mx-auto leading-relaxed">
                Tell me what you want to learn and I'll build a personalised roadmap with courses just for you.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {['Learn Python from scratch', 'Become a data scientist', 'Master React development', 'Break into ML'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full px-3.5 py-1.5 text-gray-600 dark:text-gray-300 hover:border-blue-400 dark:hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
                💡 Tip: attach your CV so I can tailor the roadmap to your background
              </p>
            </div>
          )}

          {roadmapMessageCount != null ? (
            <>
              {messages.slice(0, roadmapMessageCount).map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {roadmap && (
                <>
                  <RoadmapView roadmap={roadmap} sessionId={sessionId} />
                  <StudyCoach sessionId={sessionId} />
                </>
              )}
              {messages.slice(roadmapMessageCount).map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </>
          ) : (
            messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
          )}

          {isTyping && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input area ── */}
      <div className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 px-4 py-4">
        <div className="max-w-3xl mx-auto space-y-2">

          {/* File attachment chip */}
          {attachedFile && (
            <div className="flex items-center gap-2 px-1">
              <div className="flex items-center gap-1.5 bg-blue-50 dark:bg-blue-900/40 border border-blue-200 dark:border-blue-700 rounded-lg pl-2.5 pr-1.5 py-1.5 text-sm text-blue-700 dark:text-blue-300 max-w-xs">
                <DocIcon className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate text-xs font-medium">{attachedFile.name}</span>
                {attachedFile.truncated && <span className="text-xs opacity-60 shrink-0">truncated</span>}
                <button
                  onClick={() => { setAttachedFile(null); setFileError(null) }}
                  className="ml-0.5 p-0.5 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition shrink-0"
                  aria-label="Remove attachment"
                >
                  <XIcon />
                </button>
              </div>
            </div>
          )}

          {/* File error */}
          {fileError && (
            <p className="text-xs text-red-500 dark:text-red-400 px-1">{fileError}</p>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED}
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Unified input container */}
          <div className={`flex items-end gap-2 bg-white dark:bg-gray-800 border rounded-2xl px-3 py-2 shadow-sm transition-all ${
            disabled ? 'opacity-60' : 'border-gray-300 dark:border-gray-600 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-500/20'
          }`}>

            {/* Paperclip */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading || disabled}
              aria-label="Attach file"
              title="Attach file (PDF, Word, Excel, or text)"
              className="shrink-0 p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 dark:hover:text-blue-400 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isUploading ? <SpinnerIcon className="w-5 h-5" /> : <PaperclipIcon />}
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={
                disabled ? 'Starting session…'
                : roadmap ? 'Ask anything about your roadmap…'
                : 'Tell me what you want to learn…'
              }
              rows={1}
              className="flex-1 bg-transparent text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 text-sm resize-none focus:outline-none leading-relaxed disabled:cursor-not-allowed"
              style={{ minHeight: '24px', maxHeight: '128px' }}
            />

            {/* Mic */}
            <button
              onClick={handleMicClick}
              disabled={disabled}
              aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
              title={
                !speechSupported ? 'Speech not supported in this browser (use Chrome/Edge)'
                : isRecording ? 'Stop recording'
                : 'Click to speak'
              }
              className={`shrink-0 p-1.5 rounded-lg transition disabled:opacity-40 disabled:cursor-not-allowed ${
                isRecording
                  ? 'text-white bg-red-500 animate-pulse'
                  : 'text-gray-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/30 dark:hover:text-rose-400'
              }`}
            >
              <MicIcon />
            </button>

            {/* Send */}
            <button
              onClick={handleSend}
              disabled={!canSend}
              aria-label="Send message"
              className="shrink-0 flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/40 text-white rounded-xl px-3.5 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed"
            >
              <SendIcon />
              <span>Send</span>
            </button>
          </div>

          <p className="text-center text-xs text-gray-400 dark:text-gray-600">
            Enter to send · Shift+Enter for new line{speechSupported ? ' · 🎤 to speak' : ''}
          </p>
        </div>
      </div>

      {showHistory && (
        <HistoryPanel onClose={() => setShowHistory(false)} onLoad={handleLoadHistory} />
      )}
    </div>
  )
}
