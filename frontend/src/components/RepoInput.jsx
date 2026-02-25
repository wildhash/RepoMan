import { useState } from 'react'
import { startTransform } from '../api'

export default function RepoInput({ onJobStarted }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const { job_id } = await startTransform(url.trim())
      onJobStarted(job_id)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background">
      <h1 className="text-4xl font-bold text-accent mb-2 font-mono">RepoMan</h1>
      <p className="text-gray-400 mb-8">Multi-model agentic repository transformation</p>
      <form onSubmit={handleSubmit} className="w-full max-w-xl flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          required
          className="flex-1 bg-card border border-gray-700 rounded px-4 py-3 text-white font-mono focus:outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-accent text-black font-bold px-6 py-3 rounded hover:opacity-90 disabled:opacity-50 transition"
        >
          {loading ? 'Starting…' : 'Transform'}
        </button>
      </form>
      {error && <p className="text-red-400 mt-4">{error}</p>}
    </div>
  )
}
