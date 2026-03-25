import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { updateProfile } from '../services/api'
import useAuthStore from '../store/authStore'

const DOMAINS = [
  { value: 'backend', label: 'Backend Development' },
  { value: 'frontend', label: 'Frontend Development' },
  { value: 'fullstack', label: 'Full-Stack Development' },
  { value: 'devops', label: 'DevOps / Infrastructure' },
  { value: 'data', label: 'Data Science / ML' },
  { value: 'mobile', label: 'Mobile Development' },
  { value: 'security', label: 'Cybersecurity' },
  { value: 'cloud', label: 'Cloud Engineering' },
  { value: 'other', label: 'Other' },
]

const TECH_OPTIONS = [
  'Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust', 'C++', 'C#',
  'Ruby', 'PHP', 'Swift', 'Kotlin', 'React', 'Vue', 'Angular', 'Next.js',
  'Node.js', 'Django', 'FastAPI', 'Spring', 'Docker', 'Kubernetes', 'AWS',
  'GCP', 'Azure', 'PostgreSQL', 'MongoDB', 'Redis', 'Git', 'Linux',
]

export default function ProfileSetup() {
  const navigate = useNavigate()
  const updateUser = useAuthStore((s) => s.updateUser)

  const [form, setForm] = useState({
    full_name: '',
    bio: '',
    primary_domain: '',
    experience_years: '',
    tech_stack: [],
    current_role: '',
    education: '',
    github_url: '',
    linkedin_url: '',
  })
  const [techInput, setTechInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const bioLen = form.bio.length
  const bioValid = bioLen >= 50 && bioLen <= 500
  const canSubmit =
    form.full_name.trim() &&
    bioValid &&
    form.primary_domain &&
    form.experience_years !== '' &&
    form.tech_stack.length >= 1

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const toggleTech = (tech) => {
    setForm((f) => ({
      ...f,
      tech_stack: f.tech_stack.includes(tech)
        ? f.tech_stack.filter((t) => t !== tech)
        : [...f.tech_stack, tech],
    }))
  }

  const addCustomTech = () => {
    const t = techInput.trim()
    if (t && !form.tech_stack.includes(t)) {
      setForm((f) => ({ ...f, tech_stack: [...f.tech_stack, t] }))
    }
    setTechInput('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...form,
        experience_years: parseInt(form.experience_years, 10) || 0,
      }
      const res = await updateProfile(payload)
      updateUser(res.data.data)
      navigate('/recommendations')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const missing = []
  if (!form.full_name.trim()) missing.push('full name')
  if (!bioValid) missing.push(`bio (${bioLen < 50 ? `${50 - bioLen} more chars needed` : 'too long'})`)
  if (!form.primary_domain) missing.push('primary domain')
  if (form.experience_years === '') missing.push('experience years')
  if (form.tech_stack.length === 0) missing.push('at least one tech')

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-md p-8">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-1">Complete your profile</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">
            We need this to generate personalized roadmaps for you.
          </p>

          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm rounded-lg px-4 py-3 mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Required fields */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                name="full_name" value={form.full_name} onChange={handleChange}
                placeholder="Jane Smith"
                className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Bio <span className="text-red-500">*</span>
                <span className={`ml-2 text-xs font-normal ${bioLen < 50 ? 'text-red-400' : bioLen > 500 ? 'text-red-400' : 'text-green-500'}`}>
                  {bioLen}/500
                </span>
              </label>
              <textarea
                name="bio" value={form.bio} onChange={handleChange} rows={4}
                placeholder="Tell us about yourself, your background, and what drives you to learn (50–500 characters)..."
                className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Primary Domain <span className="text-red-500">*</span>
                </label>
                <select
                  name="primary_domain" value={form.primary_domain} onChange={handleChange}
                  className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select domain...</option>
                  {DOMAINS.map((d) => (
                    <option key={d.value} value={d.value}>{d.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Years of Experience <span className="text-red-500">*</span>
                </label>
                <input
                  name="experience_years" type="number" min="0" max="50"
                  value={form.experience_years} onChange={handleChange}
                  placeholder="e.g. 3"
                  className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tech Stack <span className="text-red-500">*</span>
                <span className="ml-2 text-xs font-normal text-gray-400">(select at least 1)</span>
              </label>
              <div className="flex flex-wrap gap-2 mb-2">
                {TECH_OPTIONS.map((tech) => (
                  <button
                    key={tech} type="button" onClick={() => toggleTech(tech)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                      form.tech_stack.includes(tech)
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-blue-400'
                    }`}
                  >
                    {tech}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  value={techInput} onChange={(e) => setTechInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addCustomTech())}
                  placeholder="Add custom tech..."
                  className="flex-1 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="button" onClick={addCustomTech}
                  className="px-4 py-2 bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-gray-500 transition"
                >
                  Add
                </button>
              </div>
              {form.tech_stack.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {form.tech_stack.map((t) => (
                    <span key={t} className="inline-flex items-center gap-1 bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-xs px-2 py-0.5 rounded-full">
                      {t}
                      <button type="button" onClick={() => toggleTech(t)} className="hover:text-red-500 ml-0.5">×</button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Optional fields */}
            <details className="group">
              <summary className="cursor-pointer text-sm text-blue-500 hover:underline select-none">
                + Add optional details (current role, education, social links)
              </summary>
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Current Role</label>
                    <input name="current_role" value={form.current_role} onChange={handleChange}
                      placeholder="e.g. Junior Developer"
                      className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Education</label>
                    <input name="education" value={form.education} onChange={handleChange}
                      placeholder="e.g. BS Computer Science"
                      className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">GitHub URL</label>
                    <input name="github_url" value={form.github_url} onChange={handleChange}
                      placeholder="https://github.com/..."
                      className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">LinkedIn URL</label>
                    <input name="linkedin_url" value={form.linkedin_url} onChange={handleChange}
                      placeholder="https://linkedin.com/in/..."
                      className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            </details>

            {/* Missing fields hint */}
            {!canSubmit && missing.length > 0 && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                Still needed: {missing.join(', ')}
              </p>
            )}

            <button
              type="submit" disabled={!canSubmit || saving}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg py-3 text-sm transition"
            >
              {saving ? 'Saving...' : 'Save Profile & Continue'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
