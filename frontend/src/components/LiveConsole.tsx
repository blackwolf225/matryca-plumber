import { useEffect, useRef } from 'react'

interface LiveConsoleProps {
  logs: string[]
}

const STICK_TO_BOTTOM_THRESHOLD_PX = 48

export function LiveConsole({ logs }: LiveConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)

  useEffect(() => {
    const el = scrollRef.current
    if (!el || !stickToBottomRef.current) return
    el.scrollTop = el.scrollHeight
  }, [logs])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    stickToBottomRef.current = distanceFromBottom <= STICK_TO_BOTTOM_THRESHOLD_PX
  }

  return (
    <section className="card-glow col-span-full flex h-[min(480px,60vh)] flex-col overflow-hidden rounded-xl border border-cyber-border bg-cyber-panel/90 backdrop-blur-sm">
      <div className="flex items-center gap-2 border-b border-slate-800 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
        <p className="ml-2 font-mono text-xs uppercase tracking-[0.2em] text-slate-500">
          Live Console
        </p>
      </div>

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="terminal-scroll min-h-0 flex-1 overflow-y-auto bg-[#070b12] p-4 font-mono text-xs text-slate-300"
      >
        {logs.length === 0 ? (
          <p className="text-slate-600">Waiting for operational logs from /api/logs…</p>
        ) : (
          logs.map((line, index) => (
            <div key={`${index}-${line.slice(0, 24)}`} className="whitespace-pre-wrap break-all py-0.5">
              <span className="mr-2 select-none text-emerald-700">›</span>
              {line}
            </div>
          ))
        )}
      </div>
    </section>
  )
}
