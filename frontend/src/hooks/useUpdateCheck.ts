import { useCallback, useEffect, useState } from 'react'

import type { UpdateCheckResponse } from '../types/daemon'
import { MATRYCA_API_BASE, matrycaAuthenticatedFetch } from '../utils/matrycaApiAuth'

export interface UpdateCheckState {
  data: UpdateCheckResponse | null
  fetchFailed: boolean
  checking: boolean
  refetch: (options?: { force?: boolean }) => Promise<void>
}

export function useUpdateCheck(enabled: boolean = true): UpdateCheckState {
  const [data, setData] = useState<UpdateCheckResponse | null>(null)
  const [fetchFailed, setFetchFailed] = useState(false)
  const [checking, setChecking] = useState(false)

  const refetch = useCallback(async (options?: { force?: boolean }) => {
    setChecking(true)
    try {
      const params = options?.force ? '?force_refresh=true' : ''
      const response = await matrycaAuthenticatedFetch(
        `${MATRYCA_API_BASE}/api/system/update-check${params}`,
        {
          headers: { Accept: 'application/json' },
        },
      )
      if (!response.ok) {
        setFetchFailed(true)
        return
      }
      const payload = (await response.json()) as UpdateCheckResponse
      setData(payload)
      setFetchFailed(false)
    } catch {
      setFetchFailed(true)
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      return
    }

    queueMicrotask(() => {
      void refetch()
    })
  }, [enabled, refetch])

  return { data, fetchFailed, checking, refetch }
}
