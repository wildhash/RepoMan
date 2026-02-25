import HealthRadar from './HealthRadar'
import DiffViewer from './DiffViewer'
import ConsensusGauge from './ConsensusGauge'

export default function ResultsDashboard({ job, transcript }) {
  if (!job) return null

  const avgScore = job.consensus?.votes
    ? Object.values(job.consensus.votes).reduce((s, v) => s + v.score, 0) / Object.keys(job.consensus.votes).length
    : 0

  return (
    <div className="space-y-6">
      {/* Score Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Before Score', value: `${job.before_score?.toFixed(1) ?? '—'}` },
          { label: 'After Score', value: `${job.after_score?.toFixed(1) ?? '—'}`, highlight: true },
          { label: 'Issues Fixed', value: job.issues_fixed ?? 0 },
          { label: 'Duration', value: `${job.total_duration_seconds?.toFixed(1) ?? '—'}s` },
        ].map((stat) => (
          <div key={stat.label} className="bg-card rounded p-4 border border-gray-800">
            <p className="text-xs text-gray-400 mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold font-mono ${stat.highlight ? 'text-accent' : 'text-white'}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Radar + Gauge */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-card rounded p-4 border border-gray-800">
          <h3 className="text-sm font-mono text-gray-400 mb-2">Health Dimensions</h3>
          <HealthRadar beforeScores={{}} afterScores={{}} />
        </div>
        <div className="bg-card rounded p-4 border border-gray-800 flex items-center justify-center">
          <ConsensusGauge score={avgScore} />
        </div>
      </div>

      {/* Changes */}
      {job.change_sets?.length > 0 && (
        <div className="bg-card rounded p-4 border border-gray-800">
          <h3 className="text-sm font-mono text-gray-400 mb-3">Applied Changes</h3>
          <DiffViewer changeSets={job.change_sets} />
        </div>
      )}
    </div>
  )
}
