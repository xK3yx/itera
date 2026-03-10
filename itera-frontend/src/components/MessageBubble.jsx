export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.isError === true

  if (isError) {
    return (
      <div className="flex justify-start mb-4">
        <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-2xl px-4 py-3 text-sm max-w-xs">
          {message.content}
        </div>
      </div>
    )
  }

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="flex flex-col items-end gap-1 max-w-xs sm:max-w-md">
          <span className="text-xs text-gray-400 dark:text-gray-500 mr-1">You</span>
          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="flex flex-col items-start gap-1 max-w-xs sm:max-w-xl">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">Itera</span>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 dark:text-gray-100 leading-relaxed ml-8">
          {message.content}
        </div>
      </div>
    </div>
  )
}