import { useEffect, useState } from 'react'
import RepoInput from './components/RepoInput'
import PipelineView from './components/PipelineView'
import AgentDebate from './components/AgentDebate'
import ResultsDashboard from './components/ResultsDashboard'
import { useWebSocket } from './hooks/useWebSocket'
import { getJob } from './api'

export default function App() {
  const [view, setView] = useState('input') // input | pipeline | results
  const [jobId, setJobId] = useState(null)
  const [job, setJob] = useState(null)
  const [currentPhase, setCurrentPhase] = useState(null)
  const [completedPhases, setCompletedPhases] = useState([])
  const { messages, status, connected } = useWebSocket(jobId)

  // Process WebSocket events
  const debateMessages = messages.filter((m) =>
    m.event === 'debate_message'
  )

  useEffect(() => {
    if (status !== 'completed' || view !== 'pipeline' || !jobId) return

    let cancelled = false
    setView('results')

    ;(async () => {
      try {
        const j = await getJob(jobId)
        if (!cancelled) setJob(j)
      } catch (err) {
        if (!cancelled) console.error('Failed to fetch job', err)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [jobId, status, view])

  const handleJobStarted = (id) => {
    setJobId(id)
    setView('pipeline')
  }

  return (
    <div className="min-h-screen bg-background text-white font-mono">
      {view === 'input' && <RepoInput onJobStarted={handleJobStarted} />}

      {(view === 'pipeline' || view === 'results') && (
        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-accent">RepoMan</h1>
            <span className={`text-xs px-2 py-1 rounded ${connected ? 'bg-green-900 text-green-400' : 'bg-gray-800 text-gray-400'}`}>
              {connected ? '● live' : '○ offline'}
            </span>
          </div>

          <div className="bg-card rounded p-4 border border-gray-800 mb-6">
            <PipelineView currentPhase={currentPhase} completedPhases={completedPhases} />
          </div>

          {debateMessages.length > 0 && (
            <div className="bg-card rounded p-4 border border-gray-800 mb-6">
              <h2 className="text-sm text-gray-400 mb-3">Agent Debate</h2>
              <AgentDebate messages={debateMessages} />
            </div>
          )}

          {view === 'results' && job && (
            <ResultsDashboard job={job} />
          )}
        </div>
      )}
    </div>
  )
}
