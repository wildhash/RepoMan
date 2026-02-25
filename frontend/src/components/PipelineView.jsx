const PHASES = ['ingestion', 'audit', 'consensus', 'execution', 'review', 'validation', 'learning']

export default function PipelineView({ currentPhase, completedPhases }) {
  return (
    <div className="flex items-center gap-2 py-4 overflow-x-auto">
      {PHASES.map((phase, i) => {
        const completed = completedPhases?.includes(phase)
        const active = phase === currentPhase
        return (
          <div key={phase} className="flex items-center gap-2">
            <div className={`
              flex flex-col items-center min-w-[80px]
              ${active ? 'text-accent' : completed ? 'text-green-400' : 'text-gray-500'}
            `}>
              <div className={`
                w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2
                ${active ? 'border-accent animate-pulse bg-accent/20' : completed ? 'border-green-400 bg-green-400/20' : 'border-gray-600'}
              `}>
                {completed ? '✓' : i + 1}
              </div>
              <span className="text-xs mt-1 capitalize font-mono">{phase}</span>
            </div>
            {i < PHASES.length - 1 && (
              <div className={`w-8 h-0.5 ${completed ? 'bg-green-400' : 'bg-gray-700'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
