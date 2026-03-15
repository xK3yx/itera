export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.isError === true

  // For user messages that include a file attachment header, show a clean file badge
  const parseUserContent = (content) => {
    const sep = '\n\n---\n\n'
    const idx = content.indexOf(sep)
    if (idx !== -1) {
      const fileBlock = content.slice(0, idx)
      const userText = content.slice(idx + sep.length)
      const m = fileBlock.match(/\[Attached file: (.+?)(?:\s*—|\])/)
      return { hasFile: true, fileName: m ? m[1].trim() : 'file', userText }
    }
    if (content.startsWith('[Attached file:')) {
      const m = content.match(/\[Attached file: (.+?)(?:\s*—|\])/)
      return { hasFile: true, fileName: m ? m[1].trim() : 'file', userText: '' }
    }
    return { hasFile: false, userText: content }
  }

  if (isError) {
    return (
      <div className="flex justify-start mb-5">
        <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-2xl px-4 py-3 text-sm max-w-md">
          ⚠️ {message.content}
        </div>
      </div>
    )
  }

  if (isUser) {
    const { hasFile, fileName, userText } = parseUserContent(message.content)
    return (
      <div className="flex justify-end mb-5">
        <div className="flex flex-col items-end gap-1 max-w-[75%]">
          <span className="text-xs text-gray-400 dark:text-gray-500 mr-1">You</span>
          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-md px-4 py-3 text-sm leading-relaxed">
            {hasFile && (
              <div className="flex items-center gap-1.5 mb-2 pb-2 border-b border-blue-500/50 text-blue-100 text-xs">
                <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="truncate max-w-[200px]">{fileName}</span>
              </div>
            )}
            {userText
              ? <p className="whitespace-pre-wrap break-words">{userText}</p>
              : !hasFile && <p className="whitespace-pre-wrap break-words">{message.content}</p>
            }
          </div>
        </div>
      </div>
    )
  }

  // Assistant message
  return (
    <div className="flex justify-start mb-5">
      <div className="flex flex-col items-start gap-1.5 max-w-[80%]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center shrink-0 shadow-sm">
            <span className="text-white text-xs font-bold leading-none">I</span>
          </div>
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">Itera</span>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-md px-4 py-3 text-sm text-gray-800 dark:text-gray-100 leading-relaxed shadow-sm ml-8">
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
      </div>
    </div>
  )
}
