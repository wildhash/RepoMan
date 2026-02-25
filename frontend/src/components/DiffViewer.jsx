import { useState } from 'react'

export default function DiffViewer({ changeSets }) {
  const [expanded, setExpanded] = useState({})

  if (!changeSets?.length) return null

  return (
    <div className="space-y-2">
      {changeSets.map((cs, i) => (
        <div key={i} className="bg-card rounded border border-gray-800">
          <button
            onClick={() => setExpanded((p) => ({ ...p, [i]: !p[i] }))}
            className="w-full flex justify-between items-center px-4 py-3 text-left"
          >
            <span className="font-mono text-sm text-accent">{cs.step_name}</span>
            <span className="text-xs text-gray-400">{cs.summary}</span>
            <span className="text-gray-500 text-sm">{expanded[i] ? '▲' : '▼'}</span>
          </button>
          {expanded[i] && (
            <div className="px-4 pb-3 space-y-1">
              {[...cs.files_created, ...cs.files_modified].map((f, j) => (
                <div key={j} className="text-xs">
                  <span className={f.action === 'create' ? 'text-green-400' : 'text-yellow-400'}>
                    {f.action === 'create' ? '+' : '~'} {f.path}
                  </span>
                  <span className="text-gray-500 ml-2">{f.summary}</span>
                </div>
              ))}
              {cs.files_deleted?.map((p, j) => (
                <div key={j} className="text-xs text-red-400">- {p}</div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
