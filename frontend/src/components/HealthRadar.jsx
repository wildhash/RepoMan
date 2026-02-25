import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Legend } from 'recharts'

const DIMENSIONS = ['architecture', 'code_quality', 'test_coverage', 'security', 'documentation', 'performance', 'maintainability', 'deployment_readiness']

export default function HealthRadar({ beforeScores, afterScores }) {
  const data = DIMENSIONS.map((dim) => ({
    subject: dim.replace('_', ' '),
    before: beforeScores?.[dim] ?? 5,
    after: afterScores?.[dim] ?? 5,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data}>
        <PolarGrid stroke="#333" />
        <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
        <Radar name="Before" dataKey="before" stroke="#ef4444" fill="#ef4444" fillOpacity={0.1} strokeDasharray="5 5" />
        <Radar name="After" dataKey="after" stroke="#22c55e" fill="#22c55e" fillOpacity={0.2} />
        <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
