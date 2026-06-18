import { AlertTriangle, CheckCircle2, Circle, Cpu, FolderPlus, Loader2, Sparkles, XCircle } from 'lucide-react'
import { useState } from 'react'

import type { PlumberConfig } from '../types/daemon'
import type { PreflightCheck, PreflightResponse, ProvisionL1Response } from '../types/preflight'

interface PreFlightModalProps {
  open: boolean
  report: PreflightResponse | null
  loading: boolean
  error: string | null
  config: PlumberConfig | null
  onRefresh: () => Promise<PreflightResponse | null>
  onSaveGraphPath: (path: string) => Promise<PlumberConfig | null>
  onProvisionL1: () => Promise<ProvisionL1Response | null>
  onOpenSettings: () => void
  onDismissWhenReady: () => void
}

const GRAPH_INPUT_CLASS =
  'w-full rounded-xl border border-theme-border/50 bg-theme-base px-3 py-2 font-mono text-xs text-theme-text outline-none transition placeholder:text-theme-muted focus:border-theme-accent/60 focus:ring-2 focus:ring-theme-accent/30'

function checkById(report: PreflightResponse | null, id: string): PreflightCheck | undefined {
  return report?.checks.find((row) => row.id === id)
}

function PreflightStepLocalLlm() {
  return (
    <li className="space-y-3">
      <h3 className="font-medium text-theme-text">4. Start your local LLM</h3>
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
              standard <strong className="text-theme-text">CPU-only machine with 16 GB of RAM</strong>. We are
              actively testing additional open models to improve that target setup.
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-theme-border/30 bg-theme-base/50 p-4">
        <div className="flex gap-3">
          <Cpu className="mt-0.5 h-5 w-5 shrink-0 text-theme-muted" aria-hidden />
          <div className="min-w-0 space-y-3">
            <h4 className="text-sm font-semibold text-theme-text">Recommended &amp; tested model</h4>
            <p className="text-xs leading-relaxed text-theme-muted">
              <strong className="text-theme-text">Gemma 4-E4b Instruct</strong> is the model we use to test and
              validate Matryca Plumber today. In Settings, set the exact model id to{' '}
              <code className="rounded bg-theme-surface px-1 py-0.5 font-mono text-[11px]">gemma-4-e4b-it</code>
              , then use <strong>Refresh models</strong> to confirm discovery.
            </p>
            <p className="text-xs leading-relaxed text-theme-muted">
              For responsive CPU inference (about 15–30 tokens/second), prefer weights in{' '}
              <strong className="text-theme-text">GGUF format</strong> at quantization{' '}
              <code className="rounded bg-theme-surface px-1 py-0.5 font-mono text-[11px]">Q4_K_M</code> or{' '}
              <code className="rounded bg-theme-surface px-1 py-0.5 font-mono text-[11px]">Q5_K_M</code>.
            </p>
            <p className="text-xs leading-relaxed text-theme-muted">
              We are actively testing additional open models to improve CPU-only, 16 GB RAM setups; Gemma
              4-E4b Instruct remains our current default recommendation.
            </p>
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
          requiring 60GB+ of RAM.
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
  config,
  onRefresh,
  onSaveGraphPath,
  onProvisionL1,
  onOpenSettings,
  onDismissWhenReady,
}: PreFlightModalProps) {
  const [refreshing, setRefreshing] = useState(false)
  const [graphPathOverride, setGraphPathOverride] = useState<string | null>(null)
  const [graphPathTouched, setGraphPathTouched] = useState(false)
  const [savingGraph, setSavingGraph] = useState(false)
  const [graphSaveErrorLocal, setGraphSaveErrorLocal] = useState<string | null>(null)
  const [provisioningL1, setProvisioningL1] = useState(false)
  const [provisionMessage, setProvisionMessage] = useState<string | null>(null)
  const [provisionError, setProvisionError] = useState<string | null>(null)

  const serverGraphPath = config?.logseq_graph_path ?? ''
  const graphPathDraft =
    graphPathTouched && graphPathOverride !== null ? graphPathOverride : serverGraphPath
  const graphCheck = checkById(report, 'logseq_graph')
  const graphSaveError = graphCheck?.status === 'pass' ? null : graphSaveErrorLocal
  const l1Check = checkById(report, 'l1_memory')
  const graphReady = graphCheck?.status === 'pass'
  const l1Ready = l1Check?.status === 'pass'
  const plannedL1Path = l1Check?.detail ?? null

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

  const handleSaveGraph = async () => {
    const trimmed = graphPathDraft.trim()
    if (!trimmed) {
      setGraphSaveErrorLocal('Enter the absolute path to your Logseq vault root (folder containing pages/).')
      return
    }
    setSavingGraph(true)
    setGraphSaveErrorLocal(null)
    try {
      const updated = await onSaveGraphPath(trimmed)
      if (updated) {
        setGraphPathTouched(false)
        setGraphPathOverride(null)
      }
      const latest = await onRefresh()
      const savedGraphCheck = checkById(latest, 'logseq_graph')
      if (savedGraphCheck?.status === 'pass') {
        setGraphSaveErrorLocal(null)
        return
      }
      setGraphSaveErrorLocal(
        savedGraphCheck?.message ?? 'Could not save graph path. Check the path and try again.',
      )
    } catch (err) {
      setGraphSaveErrorLocal(err instanceof Error ? err.message : 'Failed to save graph path')
    } finally {
      setSavingGraph(false)
    }
  }

  const handleProvisionL1 = async () => {
    setProvisioningL1(true)
    setProvisionError(null)
    setProvisionMessage(null)
    try {
      const result = await onProvisionL1()
      if (!result?.ok) {
        setProvisionError('Could not provision matryca-l1.')
        return
      }
      setProvisionMessage(result.message)
      await onRefresh()
    } catch (err) {
      setProvisionError(err instanceof Error ? err.message : 'Failed to create matryca-l1')
    } finally {
      setProvisioningL1(false)
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
            Matryca Plumber — Pre-flight checklist
          </h2>
          <p className="mt-1 text-xs text-theme-muted">
            Developed by Marco Porcellato ·{' '}
            <a
              href="https://matryca.ai"
              className="text-theme-accent underline-offset-2 hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              Matryca.ai
            </a>
          </p>
          <p className="mt-2 text-sm text-theme-muted">
            Set your test vault path first, provision session memory, then confirm your local LLM before
            starting the maintenance daemon.
          </p>
          {report?.env_created_from_example ? (
            <p className="mt-2 rounded-lg border border-theme-accent/30 bg-theme-accent-bg/20 px-3 py-2 text-xs text-theme-accent">
              A new <code className="font-mono">.env</code> was created from{' '}
              <code className="font-mono">.env.example</code> — enter your Logseq graph path below (step 2).
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

            <li className="space-y-3">
              <h3 className="font-medium text-theme-text">2. Logseq test vault (required first)</h3>
              <p className="text-theme-muted">
                Point Matryca Plumber at the <strong>root</strong> of a Logseq OG vault — the folder that
                contains <code className="font-mono text-xs">pages/</code>. Use a clone for your first run.
              </p>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium text-theme-muted">Absolute graph path</span>
                <input
                  type="text"
                  value={graphPathDraft}
                  onChange={(event) => {
                    setGraphPathTouched(true)
                    setGraphPathOverride(event.target.value)
                  }}
                  placeholder="/Users/you/Documents/my-logseq-vault"
                  className={GRAPH_INPUT_CLASS}
                  spellCheck={false}
                  autoComplete="off"
                />
              </label>
              {graphSaveError ? (
                <p className="text-xs text-red-500" role="alert">
                  {graphSaveError}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={savingGraph || !graphPathDraft.trim()}
                  onClick={() => void handleSaveGraph()}
                  className="rounded-xl border border-theme-accent/80 bg-theme-accent px-4 py-2 text-sm font-medium text-theme-accent-foreground transition hover:bg-theme-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {savingGraph ? 'Saving…' : 'Save and verify graph'}
                </button>
                {graphReady ? (
                  <span className="inline-flex items-center gap-1.5 self-center text-xs text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" aria-hidden />
                    Graph path verified
                  </span>
                ) : null}
              </div>
            </li>

            <li className="space-y-3">
              <h3 className="font-medium text-theme-text">3. L1 session memory</h3>
              <p className="text-theme-muted">
                Matryca creates a <code className="font-mono text-xs">matryca-l1/</code> folder{' '}
                <strong>next to</strong> your vault (not inside <code className="font-mono text-xs">pages/</code>
                ) for deploy rules and session context.
              </p>
              {graphReady && !l1Ready ? (
                <div className="space-y-3 rounded-xl border border-theme-border/30 bg-theme-base/50 p-4">
                  {plannedL1Path ? (
                    <p className="font-mono text-[10px] leading-relaxed text-theme-muted" title={plannedL1Path}>
                      Will create: {plannedL1Path}
                    </p>
                  ) : null}
                  {provisionMessage ? (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400" role="status">
                      {provisionMessage}
                    </p>
                  ) : null}
                  {provisionError ? (
                    <p className="text-xs text-red-500" role="alert">
                      {provisionError}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    disabled={provisioningL1 || loading}
                    onClick={() => void handleProvisionL1()}
                    className="inline-flex items-center gap-2 rounded-xl border border-theme-border px-4 py-2 text-sm text-theme-text transition hover:border-theme-accent/50 hover:text-theme-accent disabled:opacity-40"
                  >
                    {provisioningL1 ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    ) : (
                      <FolderPlus className="h-4 w-4" aria-hidden />
                    )}
                    {provisioningL1 ? 'Creating…' : 'Create matryca-l1 folder'}
                  </button>
                </div>
              ) : null}
              {l1Ready && l1Check?.detail ? (
                <p className="inline-flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="h-4 w-4" aria-hidden />
                  <span className="truncate font-mono" title={l1Check.detail}>
                    {l1Check.detail}
                  </span>
                </p>
              ) : null}
              {!graphReady ? (
                <p className="text-xs text-theme-muted">Complete step 2 before provisioning L1 memory.</p>
              ) : null}
            </li>

            <PreflightStepLocalLlm />

            <li>
              <h3 className="font-medium text-theme-text">5. First-run expectations</h3>
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
