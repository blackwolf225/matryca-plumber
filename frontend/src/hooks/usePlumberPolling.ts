import { useCallback, useEffect, useRef, useState } from 'react'

import type {
  ConnectionStatus,
  DaemonControlResponse,
  DaemonStateResponse,
  GraphAnalytics,
  PlumberConfig,
  PlumberPollSnapshot,
} from '../types/daemon'
import {
  hasGraphAnalyticsPayload,
  normalizeDaemonState,
  normalizeGraphAnalytics,
} from '../types/daemon'
import { MATRYCA_API_BASE, matrycaFetchJson } from '../utils/matrycaApiAuth'

const POLL_INTERVAL_MS = 1000

/** Treat daemon start responses that should enable live UI polling. */
function isStartAccepted(result: DaemonControlResponse): boolean {
  return result.ok || result.code === 'already_running'
}

export function usePlumberPolling(intervalMs = POLL_INTERVAL_MS): PlumberPollSnapshot {
  const [state, setState] = useState<DaemonStateResponse | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [config, setConfig] = useState<PlumberConfig | null>(null)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting')
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [frozen, setFrozen] = useState(true)
  const [engineBusy, setEngineBusy] = useState(false)
  const [engineError, setEngineError] = useState<string | null>(null)

  const stateRef = useRef<DaemonStateResponse | null>(null)
  const logsRef = useRef<string[]>([])
  const mountedRef = useRef(true)
  const intervalRef = useRef<number | null>(null)
  const frozenRef = useRef(true)
  /** True after the operator clicks Start — keeps polling even while status is still ``stopped``. */
  const telemetryLiveRef = useRef(false)

  const clearPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  const setTelemetryLive = useCallback(
    (live: boolean) => {
      telemetryLiveRef.current = live
      frozenRef.current = !live
      setFrozen(!live)
      if (!live) {
        clearPolling()
      }
    },
    [clearPolling],
  )

  const poll = useCallback(async () => {
    let stateOk = false
    let logsOk = false
    let configOk = false

    try {
      const refreshedConfig = await matrycaFetchJson<PlumberConfig>(`${MATRYCA_API_BASE}/api/config`)
      if (mountedRef.current) {
        setConfig(refreshedConfig)
        setConnectionError(null)
        configOk = true
      }
    } catch (error) {
      if (!mountedRef.current) return
      console.warn('[Matryca Plumber] poll: /api/config failed', error)
      setConnectionError(error instanceof Error ? error.message : 'config request failed')
    }

    try {
      const rawState = await matrycaFetchJson<DaemonStateResponse & { graph_analytics?: unknown }>(
        `${MATRYCA_API_BASE}/api/state`,
      )
      let graphAnalytics: GraphAnalytics | undefined = hasGraphAnalyticsPayload(rawState.graph_analytics)
        ? normalizeGraphAnalytics(rawState.graph_analytics)
        : undefined

      if (!graphAnalytics) {
        try {
          graphAnalytics = normalizeGraphAnalytics(
            await matrycaFetchJson<GraphAnalytics>(`${MATRYCA_API_BASE}/api/graph-analytics`),
          )
          if (mountedRef.current) {
            setConnectionError(null)
          }
        } catch (error) {
          console.warn('[Matryca Plumber] poll: /api/graph-analytics failed', error)
          graphAnalytics = undefined
        }
      }

      const nextState = normalizeDaemonState({
        ...rawState,
        graph_analytics: graphAnalytics,
      })
      if (!mountedRef.current) return
      stateRef.current = nextState
      setState(nextState)
      setConnectionError(null)
      stateOk = true

      if (
        frozenRef.current
        && !telemetryLiveRef.current
        && (nextState.status === 'running' || nextState.status === 'idle')
      ) {
        telemetryLiveRef.current = true
        frozenRef.current = false
        setFrozen(false)
      }
    } catch (error) {
      if (!mountedRef.current) return
      console.warn('[Matryca Plumber] poll: /api/state failed', error)
      setConnectionError(error instanceof Error ? error.message : 'state request failed')
    }

    if (frozenRef.current) {
      if (!mountedRef.current) return
      if (stateOk || configOk) {
        setConnectionStatus('live')
        setLastUpdatedAt(new Date())
      } else if (!stateRef.current) {
        setConnectionStatus('offline')
      } else {
        setConnectionStatus('connecting')
      }
      return
    }

    try {
      const nextLogs = await matrycaFetchJson<string[]>(`${MATRYCA_API_BASE}/api/logs`)
      if (!mountedRef.current) return
      const cleaned = nextLogs.filter((line) => line.trim().length > 0)
      logsRef.current = cleaned
      setLogs(cleaned)
      setConnectionError(null)
      logsOk = true
    } catch (error) {
      if (!mountedRef.current) return
      console.warn('[Matryca Plumber] poll: /api/logs failed', error)
      setConnectionError(error instanceof Error ? error.message : 'logs request failed')
    }

    if (!mountedRef.current) return
    if (stateOk || logsOk || configOk) {
      setConnectionStatus('live')
      setLastUpdatedAt(new Date())
    } else if (!stateRef.current) {
      setConnectionStatus('offline')
    } else {
      setConnectionStatus('connecting')
    }
  }, [])

  const startPollingLoop = useCallback(() => {
    clearPolling()
    intervalRef.current = window.setInterval(() => {
      void poll()
    }, intervalMs)
  }, [clearPolling, intervalMs, poll])

  useEffect(() => {
    mountedRef.current = true
    void poll()
    return () => {
      mountedRef.current = false
      clearPolling()
    }
  }, [clearPolling, poll])

  useEffect(() => {
    if (frozen) {
      clearPolling()
      return
    }
    void poll()
    startPollingLoop()
    return () => {
      clearPolling()
    }
  }, [clearPolling, frozen, poll, startPollingLoop])

  const refreshConfig = useCallback(async () => {
    try {
      const payload = await matrycaFetchJson<PlumberConfig>(`${MATRYCA_API_BASE}/api/config`)
      if (mountedRef.current) {
        setConfig(payload)
        setConnectionError(null)
      }
    } catch (error) {
      console.warn('[Matryca Plumber] refreshConfig: /api/config failed', error)
      if (mountedRef.current) {
        setConfig(null)
        setConnectionError(error instanceof Error ? error.message : 'config request failed')
      }
    }
  }, [])

  useEffect(() => {
    void refreshConfig()
  }, [refreshConfig])

  const startEngine = useCallback(async () => {
    setEngineBusy(true)
    setEngineError(null)
    try {
      const result = await matrycaFetchJson<DaemonControlResponse>(`${MATRYCA_API_BASE}/api/daemon/start`, {
        method: 'POST',
      })
      if (!isStartAccepted(result)) {
        setEngineError(result.message ?? 'Failed to start engine')
        return
      }
      setTelemetryLive(true)
      await poll()
    } catch (error) {
      if (mountedRef.current) {
        setEngineError(error instanceof Error ? error.message : 'Failed to start engine')
      }
    } finally {
      if (mountedRef.current) {
        setEngineBusy(false)
      }
    }
  }, [poll, setTelemetryLive])

  const stopEngine = useCallback(async () => {
    setEngineBusy(true)
    setEngineError(null)
    try {
      const result = await matrycaFetchJson<DaemonControlResponse>(`${MATRYCA_API_BASE}/api/daemon/stop`, {
        method: 'POST',
      })
      if (!result.ok) {
        setEngineError(result.message ?? 'Failed to stop engine')
        return
      }
      setTelemetryLive(false)
      await poll()
    } catch (error) {
      if (mountedRef.current) {
        setEngineError(error instanceof Error ? error.message : 'Failed to stop engine')
      }
    } finally {
      if (mountedRef.current) {
        setEngineBusy(false)
      }
    }
  }, [poll, setTelemetryLive])

  const saveConfig = useCallback(async (payload: PlumberConfig): Promise<PlumberConfig | null> => {
    try {
      const updated = await matrycaFetchJson<PlumberConfig>(`${MATRYCA_API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (mountedRef.current) {
        setConfig(updated)
      }
      return updated
    } catch (error) {
      if (mountedRef.current) {
        setEngineError(error instanceof Error ? error.message : 'Failed to save config')
      }
      return null
    }
  }, [])

  return {
    state,
    logs,
    config,
    connectionStatus,
    connectionError,
    lastUpdatedAt,
    frozen,
    engineBusy,
    engineError,
    startEngine,
    stopEngine,
    saveConfig,
    refreshConfig,
  }
}
