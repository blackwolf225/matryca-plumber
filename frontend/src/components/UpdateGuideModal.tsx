import { useCallback, useEffect, useRef, useState } from 'react'

interface UpdateGuideModalProps {
  open: boolean
  latestVersion: string
  onClose: () => void
}

interface InstallMethod {
  id: string
  title: string
  description: string
  commands: string
}

const INSTALL_METHODS: InstallMethod[] = [
  {
    id: 'uv-tool',
    title: 'uv tool install (recommended for services)',
    description: 'Use this if you installed Matryca via uv tool or run a background service.',
    commands: [
      '# 1. Stop the daemon (UI Stop Engine, or CLI)',
      'matryca plumber stop',
      '',
      '# 2. Upgrade the stable binary',
      'uv tool upgrade matryca-logseq',
      '',
      '# 3. Restart the control room',
      'matryca plumber status',
    ].join('\n'),
  },
  {
    id: 'git-dev',
    title: 'Git clone / developer checkout',
    description: 'Use this if you develop from a local clone of the repository.',
    commands: [
      '# 1. Stop the daemon (UI Stop Engine, or CLI)',
      'matryca plumber stop',
      '',
      '# 2. Pull and reinstall dependencies',
      'git pull && make install',
      'cd frontend && npm install && npm run build && cd ..',
      '',
      '# 3. Restart the control room',
      'matryca plumber status',
    ].join('\n'),
  },
]

function CopyableCodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)
  const copiedTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
    }
  }, [])

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      if (copiedTimeoutRef.current !== null) {
        window.clearTimeout(copiedTimeoutRef.current)
      }
      copiedTimeoutRef.current = window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }, [code])

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => void handleCopy()}
        className="absolute right-2 top-2 rounded-md border border-theme-border/60 bg-theme-surface/80 px-2 py-1 text-[10px] font-medium uppercase tracking-wider text-theme-muted transition hover:text-theme-text"
      >
        {copied ? 'Copied' : 'Copy'}
      </button>
      <pre className="overflow-x-auto rounded-xl border border-theme-accent/30 bg-theme-base p-4 pr-16 text-xs leading-relaxed text-theme-text">
        <code>{code}</code>
      </pre>
    </div>
  )
}

export function UpdateGuideModal({ open, latestVersion, onClose }: UpdateGuideModalProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    const panel = panelRef.current
    if (!panel) {
      return
    }

    const focusable = panel.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    )
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    first?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab' || focusable.length === 0) {
        return
      }
      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        }
        return
      }
      if (document.activeElement === last) {
        event.preventDefault()
        first?.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-theme-base/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="update-guide-title"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-theme-border/60 bg-theme-surface shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-4 border-b border-theme-border/50 px-5 py-4">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.35em] text-theme-muted">
              Safe guided update
            </p>
            <h2 id="update-guide-title" className="mt-1 text-base font-semibold text-theme-text">
              How to safely update
            </h2>
            <p className="mt-1 text-xs text-theme-muted">
              Version <span className="font-medium text-theme-accent">{latestVersion}</span> is
              available on PyPI.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close update guide"
            className="inline-flex h-9 shrink-0 items-center gap-2 rounded-full bg-theme-text px-4 text-black shadow-sm transition hover:opacity-90"
          >
            <span className="text-[10px] font-semibold uppercase tracking-[0.2em]">Close</span>
          </button>
        </header>

        <div className="space-y-5 px-5 py-4">
          <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-600 dark:text-amber-400">
            To prevent file corruption, Matryca Plumber must be stopped before updating.
          </div>

          <p className="text-xs leading-relaxed text-theme-muted">
            The control room cannot upgrade a running daemon in place. Stop the engine, run the
            commands below in your terminal, then reopen this dashboard.
          </p>

          {INSTALL_METHODS.map((method) => (
            <section key={method.id} className="space-y-2">
              <div>
                <h3 className="text-sm font-semibold text-theme-text">{method.title}</h3>
                <p className="mt-1 text-[11px] leading-relaxed text-theme-muted">
                  {method.description}
                </p>
              </div>
              <CopyableCodeBlock code={method.commands} />
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
