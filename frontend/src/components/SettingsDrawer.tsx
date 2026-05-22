import { useEffect, useState } from 'react'

import type { PlumberConfig } from '../types/daemon'

interface SettingsDrawerProps {
  open: boolean
  config: PlumberConfig | null
  onClose: () => void
  onSave: (payload: PlumberConfig) => Promise<PlumberConfig | null>
}

interface FieldSpec {
  key: keyof PlumberConfig
  label: string
  description: string
  type: 'text' | 'number' | 'boolean'
  step?: string
}

const FIELDS: FieldSpec[] = [
  {
    key: 'logseq_graph_path',
    label: 'Logseq Graph Path',
    description: 'Root folder of your local Logseq OG markdown vault — the daemon scans this tree.',
    type: 'text',
  },
  {
    key: 'lm_studio_url',
    label: 'LM Studio URL',
    description: 'OpenAI-compatible endpoint for your local inference server (thermal pacing applies after each call).',
    type: 'text',
  },
  {
    key: 'thermal_delay_bootstrap',
    label: 'Bootstrap Thermal Delay (s)',
    description: 'Cool-down pause after catalog/bootstrap LLM calls to protect CPU and GPU thermals.',
    type: 'number',
    step: '0.1',
  },
  {
    key: 'thermal_delay_cognitive',
    label: 'Cognitive Thermal Delay (s)',
    description: 'Cool-down pause after Phase-2 lint and enrichment inferences during graph indexing.',
    type: 'number',
    step: '0.1',
  },
  {
    key: 'mapreduce_trigger_chars',
    label: 'MapReduce Trigger (chars)',
    description: 'Giant pages above this size are split into root-tree chunks before LLM harvest.',
    type: 'number',
    step: '1000',
  },
  {
    key: 'mapreduce_chunk_chars',
    label: 'MapReduce Chunk (chars)',
    description: 'Maximum characters per chunk when hierarchical MapReduce summarization activates.',
    type: 'number',
    step: '1000',
  },
  {
    key: 'low_priority_mode',
    label: 'Hardware Guard (Low Priority)',
    description: 'Sets POSIX niceness to 19 so Plumber yields CPU cycles to your foreground work.',
    type: 'boolean',
  },
  {
    key: 'context_compression',
    label: 'Context Compression',
    description: 'Rolling condensation of multi-turn LLM history to prevent KV-cache saturation.',
    type: 'boolean',
  },
  {
    key: 'backpropagate_links',
    label: 'Link Backpropagation',
    description: 'Repairs dangling wiki-links by propagating corrections across the graph.',
    type: 'boolean',
  },
  {
    key: 'heal_dangling',
    label: 'Contextual Seeding',
    description: 'Generates seed definitions for unresolved link targets during cognitive lint.',
    type: 'boolean',
  },
]

function emptyDraft(): PlumberConfig {
  return {
    logseq_graph_path: '',
    lm_studio_url: 'http://localhost:1234/v1',
    low_priority_mode: true,
    thermal_delay_bootstrap: 2,
    thermal_delay_cognitive: 2,
    mapreduce_trigger_chars: 25000,
    mapreduce_chunk_chars: 15000,
    context_compression: false,
    backpropagate_links: false,
    heal_dangling: false,
  }
}

export function SettingsDrawer({ open, config, onClose, onSave }: SettingsDrawerProps) {
  const [draft, setDraft] = useState<PlumberConfig>(emptyDraft())
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config) {
      setDraft(config)
    }
  }, [config])

  useEffect(() => {
    if (!open) {
      setSaved(false)
    }
  }, [open])

  const updateField = <K extends keyof PlumberConfig>(key: K, raw: PlumberConfig[K]) => {
    setDraft((prev) => ({ ...prev, [key]: raw }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    const result = await onSave(draft)
    setSaving(false)
    if (result) {
      setSaved(true)
    }
  }

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300 ${
          open ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-96 transform border-r border-slate-800 bg-slate-950 shadow-2xl transition-transform duration-300 ease-out ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-hidden={!open}
        aria-label="Environment settings"
      >
        <div className="flex h-full flex-col">
          <header className="border-b border-slate-800 px-5 py-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-slate-500">
              Configuration
            </p>
            <h2 className="mt-1 font-mono text-sm font-semibold text-slate-100">Environment (.env)</h2>
            <p className="mt-1 text-xs text-slate-500">
              Changes persist to your local <code className="text-cyber-cyan">.env</code> file.
            </p>
          </header>

          <form
            className="flex-1 overflow-y-auto px-5 py-4 terminal-scroll"
            onSubmit={(event) => {
              event.preventDefault()
              void handleSave()
            }}
          >
            <div className="space-y-5">
              {FIELDS.map((field) => (
                <label key={field.key} className="block space-y-1.5">
                  <span className="font-mono text-xs font-medium text-slate-200">{field.label}</span>
                  <p className="text-[11px] leading-relaxed text-slate-500">{field.description}</p>
                  {field.type === 'boolean' ? (
                    <input
                      type="checkbox"
                      checked={Boolean(draft[field.key])}
                      onChange={(event) => updateField(field.key, event.target.checked as PlumberConfig[typeof field.key])}
                      className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-900 accent-emerald-500"
                    />
                  ) : field.type === 'number' ? (
                    <input
                      type="number"
                      step={field.step}
                      value={Number(draft[field.key])}
                      onChange={(event) =>
                        updateField(field.key, Number(event.target.value) as PlumberConfig[typeof field.key])
                      }
                      className="w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 font-mono text-xs text-slate-100 outline-none ring-cyber-cyan/40 focus:ring-2"
                    />
                  ) : (
                    <input
                      type="text"
                      value={String(draft[field.key])}
                      onChange={(event) =>
                        updateField(field.key, event.target.value as PlumberConfig[typeof field.key])
                      }
                      className="w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 font-mono text-xs text-slate-100 outline-none ring-cyber-cyan/40 focus:ring-2"
                    />
                  )}
                </label>
              ))}
            </div>
          </form>

          <footer className="border-t border-slate-800 px-5 py-4">
            <button
              type="button"
              disabled={saving}
              onClick={() => void handleSave()}
              className="w-full rounded-lg border border-emerald-500/50 bg-emerald-950/50 px-4 py-2.5 font-mono text-xs font-semibold uppercase tracking-wider text-emerald-300 shadow-[0_0_18px_rgb(52_211_153_/_0.35)] transition hover:bg-emerald-900/40 disabled:opacity-50"
            >
              {saving ? 'Saving…' : saved ? 'Saved & Applied ✓' : 'Save & Apply Changes'}
            </button>
          </footer>
        </div>
      </aside>
    </>
  )
}
