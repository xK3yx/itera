{/* Header */}
<header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
  <div className="flex items-center space-x-2">
    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center" aria-label="Itera">
      <span className="text-white text-sm font-bold">I</span>
    </div>
    <span className="font-semibold text-gray-800">Itera</span>
  </div>
  <nav className="flex items-center space-x-2" aria-label="Main navigation">
    <button
      onClick={() => setShowHistory(true)}
      aria-label="View session history"
      className="text-xs sm:text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-gray-50 transition"
    >
      History
    </button>
    <button
      onClick={handleNewSession}
      aria-label="Start new session"
      className="text-xs sm:text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-gray-50 transition"
    >
      New session
    </button>
    <button
      onClick={handleLogout}
      aria-label="Logout"
      className="text-xs sm:text-sm text-red-500 hover:text-red-700 border border-red-200 rounded-lg px-2 sm:px-3 py-1.5 hover:bg-red-50 transition"
    >
      Logout
    </button>
  </nav>
</header>