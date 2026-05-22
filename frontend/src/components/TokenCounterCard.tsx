import { useEffect, useRef, useState } from 'react'

import { formatTokenCount } from '../utils/metrics'

interface TokenCounterCardProps {
  promptTokens: number
  completionTokens: number
}

type FlashKey = 'prompt' | 'completion' | 'total'

function TokenReadout({
  label,
  value,
  flash,
}: {
  label: string
  value: number
  flash: boolean
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p
        className={`mt-2 font-mono text-3xl font-bold tabular-nums drop-shadow-md ${
          flash ? 'animate-token-flash text-emerald-300' : 'text-emerald-400'
        }`}
      >
        {formatTokenCount(value)}
      </p>
    </div>
  )
}

export function TokenCounterCard({ promptTokens, completionTokens }: TokenCounterCardProps) {
  const sessionTotal = promptTokens + completionTokens
  const prevRef = useRef({ promptTokens, completionTokens, sessionTotal })
  const [flashing, setFlashing] = useState<Record<FlashKey, boolean>>({
    prompt: false,
    completion: false,
    total: false,
  })

  useEffect(() => {
    const prev = prevRef.current
    const nextFlash: Record<FlashKey, boolean> = {
      prompt: promptTokens > prev.promptTokens,
      completion: completionTokens > prev.completionTokens,
      total: sessionTotal > prev.sessionTotal,
    }

    if (nextFlash.prompt || nextFlash.completion || nextFlash.total) {
      setFlashing(nextFlash)
      const timer = window.setTimeout(() => {
        setFlashing({ prompt: false, completion: false, total: false })
      }, 550)
      prevRef.current = { promptTokens, completionTokens, sessionTotal }
      return () => window.clearTimeout(timer)
    }

    prevRef.current = { promptTokens, completionTokens, sessionTotal }
  }, [promptTokens, completionTokens, sessionTotal])

  return (
    <section className="card-glow rounded-xl border border-cyber-border bg-cyber-panel/90 p-5 backdrop-blur-sm">
      <h2 className="font-mono text-xs uppercase tracking-[0.25em] text-slate-500">
        Token Counter — Fuel Gauge
      </h2>
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <TokenReadout label="Prompt Tokens" value={promptTokens} flash={flashing.prompt} />
        <TokenReadout
          label="Completion Tokens"
          value={completionTokens}
          flash={flashing.completion}
        />
        <TokenReadout label="Session Total" value={sessionTotal} flash={flashing.total} />
      </div>
    </section>
  )
}
