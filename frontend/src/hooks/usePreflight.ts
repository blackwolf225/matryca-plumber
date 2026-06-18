import { useCallback, useEffect, useRef, useState } from 'react'

import type { PreflightResponse } from '../types/preflight'
import { MATRYCA_API_BASE, matrycaFetchJson } from '../utils/matrycaApiAuth'

export function usePreflight() {
  const [report, setReport] = useState<PreflightResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const mountedRef = useRef(true)

  const refreshPreflight = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const payload = await matrycaFetchJson<PreflightResponse>(`${MATRYCA_API_BASE}/api/preflight`)
      if (!mountedRef.current) {
        return payload
      }
      setReport(payload)
      return payload
    } catch (err) {
      if (!mountedRef.current) {
        return null
      }
      setError(err instanceof Error ? err.message : 'Pre-flight check failed')
      setReport(null)
      return null
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    queueMicrotask(() => {
      void refreshPreflight()
    })
    return () => {
      mountedRef.current = false
    }
  }, [refreshPreflight])

  const preflightReady = report?.ready === true

  return {
    report,
    loading,
    error,
    preflightReady,
    refreshPreflight,
  }
}
