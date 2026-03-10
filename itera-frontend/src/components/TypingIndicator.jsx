export default function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="flex flex-col items-start gap-1">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
            <span className="text-white text-xs font-bold">AI</span>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500">Itera</span>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 ml-8">
          <div className="flex space-x-1.5 items-center h-4">
            <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      </div>
    </div>
  )
}