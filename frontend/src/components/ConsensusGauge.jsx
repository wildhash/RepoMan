export default function ConsensusGauge({ score }) {
  const clamped = Math.min(Math.max(score ?? 0, 0), 10)
  const pct = (clamped / 10) * 100
  const color = clamped < 5 ? '#ef4444' : clamped < 7 ? '#f59e0b' : '#22c55e'
  const r = 54
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <div className="flex flex-col items-center">
      <svg width={140} height={140} viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#1f2937" strokeWidth="14" />
        <circle
          cx="70" cy="70" r={r} fill="none"
          stroke={color} strokeWidth="14"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x="70" y="70" textAnchor="middle" dominantBaseline="central" fill={color} fontSize="24" fontWeight="bold">
          {clamped.toFixed(1)}
        </text>
        <text x="70" y="92" textAnchor="middle" fill="#9ca3af" fontSize="10">/ 10</text>
      </svg>
      <p className="text-gray-400 text-sm mt-1">Consensus Score</p>
    </div>
  )
}
