import { LOW_PRIORITY_NICENESS, type PlumberConfig } from '../types/daemon'

interface HardeningShieldCardProps {
  config: PlumberConfig | null
}

function IndicatorRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[1fr_auto] gap-4 border-b border-slate-800/80 py-2.5 last:border-b-0">
      <span className="font-mono text-xs text-slate-500">{label}</span>
      <span className="font-mono text-xs font-medium text-slate-200">{value}</span>
    </div>
  )
}

export function HardeningShieldCard({ config }: HardeningShieldCardProps) {
  const nicenessLabel = config?.low_priority_mode
    ? `${LOW_PRIORITY_NICENESS} — Low Priority`
    : '0 — Normal Priority'

  return (
    <section className="card-glow rounded-xl border border-cyber-border bg-cyber-panel/90 p-5 backdrop-blur-sm">
      <h2 className="font-mono text-xs uppercase tracking-[0.25em] text-slate-500">
        Hardening Shield
      </h2>
      {!config ? (
        <p className="mt-4 font-mono text-xs text-slate-600">Loading live config from /api/config…</p>
      ) : (
        <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950/50 px-4">
          <IndicatorRow label="Process Niceness" value={nicenessLabel} />
          <IndicatorRow
            label="Thermal Delay (Bootstrap)"
            value={`${config.thermal_delay_bootstrap.toFixed(1)}s`}
          />
          <IndicatorRow
            label="Thermal Delay (Cognitive)"
            value={`${config.thermal_delay_cognitive.toFixed(1)}s`}
          />
          <IndicatorRow
            label="MapReduce Trigger"
            value={`${config.mapreduce_trigger_chars.toLocaleString()} chars`}
          />
          <IndicatorRow
            label="MapReduce Chunk"
            value={`${config.mapreduce_chunk_chars.toLocaleString()} chars`}
          />
        </div>
      )}
    </section>
  )
}
