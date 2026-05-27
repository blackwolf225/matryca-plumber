/** Mirrors ``PreflightResponse`` from ``src/cli/ui_server.py``. */

export type PreflightStatus = 'pass' | 'fail' | 'warn'

export interface PreflightCheck {
  id: string
  title: string
  status: PreflightStatus
  message: string
  detail: string | null
}

export interface PreflightResponse {
  ready: boolean
  env_created_from_example: boolean
  checks: PreflightCheck[]
}

export interface ProvisionL1Response {
  ok: boolean
  l1_path: string
  created: boolean
  message: string
}
