import http from './client'
import type { BacktestResult, JobInfo } from './types'

export interface BacktestSubmit {
  config: Record<string, unknown>
  label?: string
}

export const backtestApi = {
  submit(req: BacktestSubmit) {
    return http.post<{ job_id: string }>('/backtests', req).then(r => r.data)
  },
  get(jobId: string) {
    return http.get<JobInfo>(`/backtests/${jobId}`).then(r => r.data)
  },
  list() {
    return http.get<JobInfo[]>('/backtests').then(r => r.data)
  },
  result(jobId: string) {
    return http.get<BacktestResult>(`/backtests/${jobId}/result`).then(r => r.data)
  },
  cancel(jobId: string) {
    return http.delete<{ cancelled: boolean }>(`/backtests/${jobId}`).then(r => r.data)
  },
  watch(jobId: string, onUpdate: (info: JobInfo) => void): WebSocket {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/api/backtests/${jobId}/ws`)
    ws.onmessage = (ev) => {
      try {
        onUpdate(JSON.parse(ev.data))
      } catch {
        // ignore non-JSON frames
      }
    }
    return ws
  },
}
