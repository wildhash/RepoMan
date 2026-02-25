const AGENT_COLORS = {
  Architect: 'text-blue-400',
  Auditor: 'text-amber-400',
  Builder: 'text-green-400',
  Orchestrator: 'text-purple-400',
}

const ROLE_BADGES = {
  PROPOSAL: 'bg-blue-900 text-blue-300',
  CRITIQUE: 'bg-red-900 text-red-300',
  REVISION: 'bg-yellow-900 text-yellow-300',
  VOTE: 'bg-purple-900 text-purple-300',
  SYNTHESIS: 'bg-teal-900 text-teal-300',
  FINAL_DECISION: 'bg-green-900 text-green-300',
}

function VoteBar({ score }) {
  const pct = (score / 10) * 100
  const color = score < 5 ? 'bg-red-500' : score < 7 ? 'bg-yellow-500' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="w-24 h-2 bg-gray-700 rounded">
        <div className={`h-2 rounded ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400">{score.toFixed(1)}/10</span>
    </div>
  )
}

export default function AgentDebate({ messages }) {
  return (
    <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
      {messages.map((msg, i) => {
        const parsed = msg?.data
        if (!parsed?.agent) return null
        const colorClass = AGENT_COLORS[parsed.agent] || 'text-gray-300'
        const badgeClass = ROLE_BADGES[parsed.role] || 'bg-gray-800 text-gray-400'
        let content = parsed.content || ''
        try { content = JSON.stringify(JSON.parse(content), null, 2) } catch {}
        const scoreMatch = content.match(/"score":\s*([\d.]+)/)
        const score = scoreMatch ? parseFloat(scoreMatch[1]) : null

        return (
          <div key={i} className="bg-card rounded p-3 border border-gray-800">
            <div className="flex items-center gap-2 mb-1">
              <span className={`font-bold font-mono text-sm ${colorClass}`}>{parsed.agent}</span>
              <span className={`text-xs px-2 py-0.5 rounded font-mono ${badgeClass}`}>{parsed.role}</span>
            </div>
            {score !== null && <VoteBar score={score} />}
            <pre className="text-xs text-gray-400 mt-2 whitespace-pre-wrap font-mono max-h-32 overflow-y-auto">
              {content.slice(0, 300)}{content.length > 300 ? '…' : ''}
            </pre>
          </div>
        )
      })}
    </div>
  )
}
