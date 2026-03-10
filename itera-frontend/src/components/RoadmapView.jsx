import { useState } from 'react'

function getSearchUrl(platform, title) {
  const query = encodeURIComponent(title)
  const p = platform?.toLowerCase() || ''
  if (p.includes('coursera')) return `https://www.coursera.org/search?query=${query}`
  if (p.includes('udemy')) return `https://www.udemy.com/courses/search/?q=${query}`
  if (p.includes('youtube')) return `https://www.youtube.com/results?search_query=${query}`
  if (p.includes('freecodecamp')) return `https://www.freecodecamp.org/news/search/?query=${query}`
  if (p.includes('pluralsight')) return `https://www.pluralsight.com/search?q=${query}`
  if (p.includes('edx')) return `https://www.edx.org/search?q=${query}`
  if (p.includes('linkedin')) return `https://www.linkedin.com/learning/search?keywords=${query}`
  return `https://www.google.com/search?q=${query}+${encodeURIComponent(platform || 'course')}`
}

function CourseCard({ course }) {
  const url = getSearchUrl(course.platform, course.title)
  return (
   <a 
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="block border border-gray-200 dark:border-gray-600 rounded-xl p-4 hover:border-blue-300 dark:hover:border-blue-500 hover:shadow-sm transition bg-white dark:bg-gray-800"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-100 leading-snug">{course.title}</p>
          {course.why_recommended && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{course.why_recommended}</p>
          )}
        </div>
        <span className="shrink-0 text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium px-2 py-1 rounded-lg">
          {course.platform}
        </span>
      </div>
      <div className="flex items-center gap-3 mt-3 text-xs text-gray-400 dark:text-gray-500">
        {course.duration && <span>⏱ {course.duration}</span>}
        {course.level && <span>📊 {course.level}</span>}
        <span className="ml-auto text-blue-500 dark:text-blue-400 font-medium">Search course →</span>
      </div>
    </a>
  )
}

function TopicItem({ topic }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-gray-200 dark:border-gray-600 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left"
      >
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
          <span className="text-sm font-medium text-gray-800 dark:text-gray-100">{topic.name}</span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-400 dark:text-gray-500">{topic.estimated_hours}h</span>
          <span className="text-gray-400 dark:text-gray-500 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-700">
          {topic.description && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-3 mb-3">{topic.description}</p>
          )}
          {topic.why_relevant && (
            <p className="text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded-lg px-3 py-2 mb-3">
              💡 {topic.why_relevant}
            </p>
          )}
          {topic.courses?.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                Recommended Courses
              </p>
              {topic.courses.map((course, i) => (
                <CourseCard key={i} course={course} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function SkillArea({ area, index }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-2xl overflow-hidden shadow-sm">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
            {index + 1}
          </div>
          <div>
            <p className="font-semibold text-gray-800 dark:text-gray-100">{area.name}</p>
            {area.description && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{area.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-3 py-1 rounded-full font-medium">
            {area.estimated_hours}h
          </span>
          <span className="text-gray-400 dark:text-gray-500 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && area.topics?.length > 0 && (
        <div className="px-5 pb-5 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-100 dark:border-gray-700 space-y-2 pt-3">
          {area.topics.map((topic, i) => (
            <TopicItem key={i} topic={topic} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function RoadmapView({ roadmap }) {
  if (!roadmap) return null

  // Calculate defaults if not provided by backend
  const totalHours = roadmap.total_estimated_hours
  const weeklyHours = roadmap.weekly_hours ?? 10
  const estimatedWeeks = roadmap.estimated_weeks ?? (totalHours ? Math.ceil(totalHours / weeklyHours) : null)

  return (
    <div className="mt-6 bg-gray-50 dark:bg-gray-900/50 rounded-2xl p-5 border border-gray-200 dark:border-gray-700">
      <div className="mb-5">
        <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">🗺 Your Learning Roadmap</h2>
        {roadmap.goal && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{roadmap.goal}</p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {totalHours ?? 'N/A'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Total hours</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {weeklyHours}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Hours/week</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-700">
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {estimatedWeeks ?? 'N/A'}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Weeks</p>
        </div>
      </div>

      <div className="space-y-3">
        {roadmap.skill_areas?.map((area, i) => (
          <SkillArea key={i} area={area} index={i} />
        ))}
      </div>
    </div>
  )
}