import { useState } from 'react'

import type { ConnectionStatus, DaemonStateResponse, PlumberConfig } from '../types/daemon'
import { isEngineActive } from '../types/daemon'
import { basenameFromPath } from '../utils/metrics'
import { SettingsDrawer } from './SettingsDrawer'

interface MasterHeaderProps {
  state: DaemonStateResponse | null
  connectionStatus: ConnectionStatus
  lastUpdatedAt: Date | null
  config: PlumberConfig | null
  frozen: boolean
  engineBusy: boolean
  onStartEngine: () => Promise<void>
  onStopEngine: () => Promise<void>
  onSaveConfig: (payload: PlumberConfig) => Promise<PlumberConfig | null>
}

function connectionBadge(connectionStatus: ConnectionStatus): {
  label: string
  className: string
} {
  switch (connectionStatus) {
    case 'live':
      return {
        label: 'LINKED',
        className: 'border-emerald-500/40 bg-emerald-950/40 text-emerald-300',
      }
    case 'connecting':
      return {
        label: 'CONNECTING…',
        className: 'border-amber-500/40 bg-amber-950/40 text-amber-300 animate-pulse',
      }
    case 'offline':
      return {
        label: 'OFFLINE',
        className: 'border-red-500/40 bg-red-950/40 text-red-300',
      }
  }
}

export function MasterHeader({
  state,
  connectionStatus,
  lastUpdatedAt,
  config,
  frozen,
  engineBusy,
  onStartEngine,
  onStopEngine,
  onSaveConfig,
}: MasterHeaderProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const link = connectionBadge(connectionStatus)
  const daemonStatus = state?.status ?? 'stopped'
  const engineRunning = isEngineActive(daemonStatus) && !frozen
  const isRunning = daemonStatus === 'running'
  const isIdle = daemonStatus === 'idle'

  const statusBadgeClass = engineRunning
    ? isRunning
      ? 'border-emerald-400/60 bg-emerald-950/50 text-emerald-300 animate-pulse-glow animate-status-pulse'
      : 'border-amber-400/50 bg-amber-950/40 text-amber-300'
    : 'border-slate-500/50 bg-slate-900/60 text-slate-300'

  const statusLabel = frozen
    ? '● FROZEN'
    : isRunning
      ? '● RUNNING'
      : isIdle
        ? '● IDLE'
        : `● ${daemonStatus.toUpperCase()}`

  const phaseLabel = state?.bootstrap_complete
    ? 'Bootstrap Complete'
    : 'Phase 1: Cataloging Graph'

  const phaseClass = state?.bootstrap_complete ? 'text-cyber-cyan' : 'text-slate-400'

  return (
    <>
      <header className="card-glow col-span-full rounded-xl border border-cyber-border bg-cyber-panel/90 p-5 backdrop-blur-sm">
        <div className="flex flex-col gap-3">
          {/* Row 1: hamburger + title aligned with engine controls */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <button
                type="button"
                onClick={() => setDrawerOpen(true)}
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-700 bg-slate-900/80 text-slate-300 transition hover:border-cyber-cyan/50 hover:text-cyber-cyan"
                aria-label="Open settings"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <path d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <p className="font-mono text-xs uppercase tracking-[0.35em] text-slate-500">
                Matryca Plumber — Control Room
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                disabled={engineBusy || engineRunning}
                onClick={() => void onStartEngine()}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-emerald-500/60 bg-emerald-950/60 px-4 font-mono text-xs font-bold uppercase tracking-wider text-emerald-300 shadow-[0_0_16px_rgb(52_211_153_/_0.3)] transition hover:bg-emerald-900/50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Start Engine
              </button>
              <button
                type="button"
                disabled={engineBusy || frozen}
                onClick={() => void onStopEngine()}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-red-500/60 bg-red-950/60 px-4 font-mono text-xs font-bold uppercase tracking-wider text-red-300 shadow-[0_0_16px_rgb(248_113_113_/_0.25)] transition hover:bg-red-900/50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Stop Engine
              </button>
            </div>
          </div>

          {/* Row 2: status + telemetry, indented to title column */}
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 pl-[52px]">
            <div className="flex flex-wrap items-center gap-3">
              <span
                className={`inline-flex items-center rounded-full border px-4 py-1.5 font-mono text-sm font-semibold tracking-wide ${statusBadgeClass}`}
              >
                {statusLabel}
              </span>
              <span className={`font-mono text-sm font-medium ${phaseClass}`}>{phaseLabel}</span>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1">
              <span
                className={`inline-flex items-center rounded-md border px-2.5 py-1 font-mono text-xs uppercase tracking-wider ${link.className}`}
              >
                {link.label}
              </span>
              {state && (
                <p className="font-mono text-xs text-slate-500">
                  Model <span className="text-slate-300">{state.model}</span>
                  {state.last_file && (
                    <>
                      {' · '}
                      Last <span className="text-cyber-cyan">{basenameFromPath(state.last_file)}</span>
                    </>
                  )}
                </p>
              )}
              {lastUpdatedAt && !frozen && (
                <p className="font-mono text-[10px] text-slate-600">
                  Sync {lastUpdatedAt.toLocaleTimeString()}
                </p>
              )}
              {frozen && (
                <p className="font-mono text-[10px] text-slate-600">Telemetry paused — zero client CPU</p>
              )}
            </div>
          </div>
        </div>
      </header>

      <SettingsDrawer
        open={drawerOpen}
        config={config}
        onClose={() => setDrawerOpen(false)}
        onSave={onSaveConfig}
      />
    </>
  )
}
