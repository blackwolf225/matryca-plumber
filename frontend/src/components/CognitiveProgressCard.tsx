import type { DaemonStateResponse } from '../types/daemon'
import { computeProgressMetrics } from '../utils/metrics'

interface CognitiveProgressCardProps {
  state: DaemonStateResponse | null
}

export function CognitiveProgressCard({ state }: CognitiveProgressCardProps) {
  const metrics = state
    ? computeProgressMetrics(state)
    : {
        title: 'Awaiting daemon state…',
        subtitle: '—',
        done: 0,
        total: 0,
        percent: 0,
      }

  return (
    <section className="card-glow rounded-xl border border-cyber-border bg-cyber-panel/90 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="font-mono text-xs uppercase tracking-[0.25em] text-slate-500">
            Cognitive Progress
          </h2>
          <p className="mt-1 font-mono text-sm text-slate-200">{metrics.title}</p>
        </div>
        <span className="font-mono text-lg font-semibold text-cyber-cyan">
          {metrics.percent.toFixed(1)}%
        </span>
      </div>

      <div className="relative h-4 overflow-hidden rounded-full bg-slate-900 ring-1 ring-slate-700/80">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-600 via-cyber-cyan to-emerald-400 transition-all duration-700 ease-out"
          style={{ width: `${metrics.percent}%` }}
        />
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-emerald-400/20 blur-sm transition-all duration-700"
          style={{ width: `${metrics.percent}%` }}
        />
      </div>

      <p className="mt-3 font-mono text-xs text-slate-500">{metrics.subtitle}</p>
      {state && !state.bootstrap_complete && state.phase2_llm_turns > 0 && (
        <p className="mt-1 font-mono text-[10px] text-slate-600">
          Phase 2 turns queued: {state.phase2_llm_turns}
        </p>
      )}
    </section>
  )
}
