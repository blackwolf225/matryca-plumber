import { AlertTriangle, CheckCircle2, Circle, Cpu, Loader2, Sparkles, XCircle } from 'lucide-react'
import { useState } from 'react'

import type { PreflightCheck, PreflightResponse } from '../types/preflight'

interface PreFlightModalProps {
  open: boolean
  report: PreflightResponse | null
  loading: boolean
  error: string | null
  onRefresh: () => Promise<PreflightResponse | null>
  onOpenSettings: () => void
  onDismissWhenReady: () => void
}

function PreflightStepLocalLlm() {
  return (
    <li className="space-y-3">
      <h3 className="font-medium text-theme-text">3. Start your local LLM</h3>
      <p className="text-theme-muted">
        Start an OpenAI-compatible server (LM Studio, Ollama, etc.). In Settings, set the base URL (e.g.{' '}
        <code className="font-mono text-xs">http://localhost:1234/v1</code>) and the exact model id, then
        use <strong>Refresh models</strong> to confirm discovery.
      </p>

      <div className="space-y-3 rounded-xl border border-theme-accent/25 bg-theme-accent-bg/15 p-4 ring-1 ring-theme-accent/10">
        <div className="flex gap-3">
          <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-theme-accent" aria-hidden />
          <div className="min-w-0 space-y-2">
            <h4 className="text-sm font-semibold text-theme-text">
              🌍 The Matryca.ai Mission: Democratizing Local AI
            </h4>
            <p className="text-xs leading-relaxed text-theme-muted">
              We engineer our tools to run flawlessly on standard hardware. You do not need expensive cloud
              subscriptions or high-end GPUs. Matryca Plumber is designed to run completely offline on a
              standard <strong className="text-theme-text">CPU-only machine with 16 GB of RAM</strong>.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-theme-border/30 bg-theme-base/50 p-4">
        <div className="flex gap-3">
          <Cpu className="mt-0.5 h-5 w-5 shrink-0 text-theme-muted" aria-hidden />
          <div className="min-w-0 space-y-3">
            <h4 className="text-sm font-semibold text-theme-text">🧠 Recommended Models (May 2026)</h4>
            <p className="text-xs leading-relaxed text-theme-muted">
              To achieve maximum performance (20–30 tokens/second) without melting your CPU, download models
              in <strong className="text-theme-text">GGUF format</strong> (quantization{' '}
              <code className="rounded bg-theme-surface px-1 py-0.5 font-mono text-[11px]">Q4_K_M</code> or{' '}
              <code className="rounded bg-theme-surface px-1 py-0.5 font-mono text-[11px]">Q5_K_M</code>).
            </p>
            <div>
              <p className="text-xs font-medium text-theme-text">
                Top Picks for 16GB CPU-only machines:
              </p>
              <ul className="mt-2 space-y-2 text-xs leading-relaxed text-theme-muted">
                <li className="flex gap-2">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-theme-accent" aria-hidden />
                  <span>
                    <strong className="text-theme-text">Qwen 3.5 (1.5B or 3B):</strong> The current reigning
                    champion of lightweight open-weights. Extremely fast and highly capable of following
                    strict formatting instructions.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-theme-accent" aria-hidden />
                  <span>
                    <strong className="text-theme-text">Ministral 3 (3B):</strong> Mistral&apos;s lightweight
                    genius. Exceptional at generating the rigorous JSON metadata required by Matryca&apos;s
                    semantic engine.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-theme-accent" aria-hidden />
                  <span>
                    <strong className="text-theme-text">Llama 3.2 (3B):</strong> A solid, reliable fallback for
                    dense CPU tasks.
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div
        className="flex gap-3 rounded-xl border border-amber-500/35 bg-amber-500/10 p-4 dark:border-amber-400/30 dark:bg-amber-500/5"
        role="note"
      >
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden />
        <p className="text-xs leading-relaxed text-amber-950 dark:text-amber-100/90">
          <strong className="font-semibold">⚠️ Hardware Warning:</strong> Avoid new &quot;MoE&quot; (Mixture of
          Experts) models like <em>Llama 4 Scout</em>. Even though they advertise a low number of
          &quot;active&quot; parameters per token, the entire model weights (100B+) must be loaded into memory,
          requiring 60GB+ of RAM. Stick to the dense 1.5B – 3B models listed above.
        </p>
      </div>
    </li>
  )
}

function StatusIcon({ status }: { status: PreflightCheck['status'] }) {
  if (status === 'pass') {
    return <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" aria-hidden />
  }
  if (status === 'fail') {
    return <XCircle className="h-5 w-5 shrink-0 text-red-500" aria-hidden />
  }
  return <Circle className="h-5 w-5 shrink-0 text-amber-500" aria-hidden />
}

export function PreFlightModal({
  open,
  report,
  loading,
  error,
  onRefresh,
  onOpenSettings,
  onDismissWhenReady,
}: PreFlightModalProps) {
  const [refreshing, setRefreshing] = useState(false)

  if (!open) {
    return null
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preflight-title"
    >
      <div className="flex max-h-[min(90vh,720px)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-theme-border/40 bg-theme-surface shadow-xl">
        <div className="border-b border-theme-border/30 px-6 py-5">
          <h2 id="preflight-title" className="text-lg font-semibold text-theme-text">
            Pre-flight checklist
          </h2>
          <p className="mt-1 text-sm text-theme-muted">
            Matryca provisions your environment automatically where possible. Complete the checks below
            before starting the maintenance daemon.
          </p>
          {report?.env_created_from_example ? (
            <p className="mt-2 rounded-lg border border-theme-accent/30 bg-theme-accent-bg/20 px-3 py-2 text-xs text-theme-accent">
              A new <code className="font-mono">.env</code> was created from{' '}
              <code className="font-mono">.env.example</code> with safe defaults — open Settings to set your
              Logseq graph path and LLM endpoint.
            </p>
          ) : null}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          <ol className="space-y-6 text-sm text-theme-text">
            <li>
              <h3 className="font-medium text-theme-text">1. Control room connection</h3>
              <p className="mt-1 text-theme-muted">
                You are viewing this dashboard, so the local API is running. Keep this window open while the
                engine runs.
              </p>
            </li>

            <li>
              <h3 className="font-medium text-theme-text">2. Logseq graph (test vault first)</h3>
              <p className="mt-1 text-theme-muted">
                Point Matryca at the <strong>root</strong> of a Logseq OG vault — the folder that contains{' '}
                <code className="font-mono text-xs">pages/</code>. Use a clone for your first run; avoid
                enabling Logseq Sync on test graphs.
              </p>
              <p className="mt-1 text-theme-muted">
                Open <strong>Settings</strong> (gear) → <strong>Logseq Graph Path</strong>, enter an absolute
                path, and save.
              </p>
            </li>

            <PreflightStepLocalLlm />

            <li>
              <h3 className="font-medium text-theme-text">4. First-run expectations</h3>
              <p className="mt-1 text-theme-muted">
                Phase 1 catalogs the entire graph and may take a long time on large vaults. Phase 2 processes
                roughly one LLM-heavy page per poll interval by default.
              </p>
            </li>
          </ol>

          <div className="mt-6 rounded-xl border border-theme-border/30 bg-theme-base/40 p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-xs font-medium uppercase tracking-[0.2em] text-theme-muted">
                Live checks
              </h3>
              <button
                type="button"
                disabled={loading || refreshing}
                onClick={() => void handleRefresh()}
                className="rounded-md border border-theme-border px-2.5 py-1 text-xs text-theme-muted transition hover:border-theme-accent/50 hover:text-theme-accent disabled:opacity-40"
              >
                {loading || refreshing ? 'Checking…' : 'Re-run checks'}
              </button>
            </div>

            {error ? (
              <p className="text-xs text-red-500" role="alert">
                {error}
              </p>
            ) : null}

            <ul className="space-y-3">
              {(report?.checks ?? []).map((check) => (
                <li
                  key={check.id}
                  className="flex gap-3 rounded-lg border border-theme-border/25 bg-theme-surface/60 px-3 py-2.5"
                >
                  <StatusIcon status={check.status} />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-theme-text">{check.title}</p>
                    <p className="text-xs text-theme-muted">{check.message}</p>
                    {check.detail ? (
                      <p className="mt-1 truncate font-mono text-[10px] text-theme-muted/80" title={check.detail}>
                        {check.detail}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
              {loading && !report ? (
                <li className="flex items-center gap-2 text-xs text-theme-muted">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Running pre-flight checks…
                </li>
              ) : null}
            </ul>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-theme-border/30 px-6 py-4">
          <button
            type="button"
            onClick={onOpenSettings}
            className="rounded-xl border border-theme-border px-4 py-2 text-sm text-theme-text transition hover:border-theme-accent/50"
          >
            Open Settings
          </button>
          <button
            type="button"
            disabled={!report?.ready || loading}
            onClick={onDismissWhenReady}
            className="rounded-xl border border-theme-accent/80 bg-theme-accent px-4 py-2 text-sm font-medium text-theme-accent-foreground transition hover:bg-theme-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {report?.ready ? 'Continue to dashboard' : 'Waiting for green checks…'}
          </button>
        </div>
      </div>
    </div>
  )
}
