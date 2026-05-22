import type { DaemonStateResponse } from '../types/daemon'

export interface ProgressMetrics {
  title: string
  subtitle: string
  done: number
  total: number
  percent: number
}

export function computeProgressMetrics(state: DaemonStateResponse): ProgressMetrics {
  if (!state.bootstrap_complete) {
    const entries = Object.values(state.files)
    const processed = entries.filter((file) => file.status === 'processed').length
    const total = entries.length
    const percent = total > 0 ? Math.min(100, (processed / total) * 100) : 0
    return {
      title: 'Phase 1: Cataloging Graph',
      subtitle: `${processed} / ${total} pages indexed`,
      done: processed,
      total,
      percent,
    }
  }

  const clusterId = state.current_cluster ?? '—'
  const done = state.current_cluster_files_done
  const total = state.current_cluster_files_total
  const percent = total > 0 ? Math.min(100, (done / total) * 100) : 0

  return {
    title: `Phase 2: Semantic Neighborhood Cluster [${clusterId}]`,
    subtitle: `${done} / ${total} cluster files`,
    done,
    total,
    percent,
  }
}

export function formatTokenCount(value: number): string {
  return value.toLocaleString('en-US')
}

export function basenameFromPath(path: string | null): string | null {
  if (!path) return null
  const segments = path.split(/[/\\]/)
  return segments[segments.length - 1] ?? path
}
