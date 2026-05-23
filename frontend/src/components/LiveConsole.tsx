import type { ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'

interface LiveConsoleProps {
  logs: string[]
  telemetry?: ReactNode
}

interface LogEntry {
  id: number
  text: string
}

const STICK_TO_BOTTOM_THRESHOLD_PX = 48

export function LiveConsole({ logs, telemetry }: LiveConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const stickToBottomRef = useRef(true)
  const nextLogIdRef = useRef(0)
  const [entries, setEntries] = useState<LogEntry[]>([])

  useEffect(() => {
    setEntries((previous) => {
      if (logs.length === 0) {
        return []
      }
      if (
        logs.length >= previous.length
        && logs.slice(0, previous.length).every((line, index) => line === previous[index]?.text)
      ) {
        const appended = logs.slice(previous.length).map((text) => ({
          id: nextLogIdRef.current++,
          text,
        }))
        return [...previous, ...appended]
      }
      return logs.map((text, index) => {
        const existing = previous[index]
        if (existing && existing.text === text) {
          return existing
        }
        return { id: nextLogIdRef.current++, text }
      })
    })
  }, [logs])

  useEffect(() => {
    const el = scrollRef.current
    if (!el || !stickToBottomRef.current) return
    el.scrollTop = el.scrollHeight
  }, [entries])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    stickToBottomRef.current = distanceFromBottom <= STICK_TO_BOTTOM_THRESHOLD_PX
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl bg-theme-surface/45 shadow-sm ring-1 ring-theme-border/25 dark:bg-theme-surface/20">
      {telemetry}

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="markdown-theme terminal-scroll min-h-0 flex-1 space-y-1.5 overflow-y-auto bg-theme-base p-4 text-sm"
      >
        {entries.length === 0 ? (
          <p className="text-theme-muted">Waiting for operational logs from /api/logs…</p>
        ) : (
          entries.map((entry) => (
            <div
              key={entry.id}
              className="rounded-lg border border-theme-border/45 bg-theme-surface/60 px-3 py-1.5 font-mono text-xs shadow-sm"
            >
              <span className="mr-2 select-none text-emerald-500">›</span>
              <span className="whitespace-pre-wrap break-all text-theme-text">{entry.text}</span>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
