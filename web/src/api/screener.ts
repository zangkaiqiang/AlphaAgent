import http from './client'
import type { ScreenerJobInfo, ScreenResult, ScreenerRulesCatalog } from './types'

export interface ScreenerSubmit {
  config: Record<string, unknown>
  label?: string
}

export const screenerApi = {
  submit(req: ScreenerSubmit) {
    return http.post<{ job_id: string }>('/screeners', req).then(r => r.data)
  },
  get(jobId: string) {
    return http.get<ScreenerJobInfo>(`/screeners/${jobId}`).then(r => r.data)
  },
  list() {
    return http.get<ScreenerJobInfo[]>('/screeners').then(r => r.data)
  },
  result(jobId: string) {
    return http.get<ScreenResult>(`/screeners/${jobId}/result`).then(r => r.data)
  },
  cancel(jobId: string) {
    return http.delete<{ cancelled: boolean }>(`/screeners/${jobId}`).then(r => r.data)
  },
  watch(jobId: string, onUpdate: (info: ScreenerJobInfo) => void): WebSocket {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/api/screeners/${jobId}/ws`)
    ws.onmessage = (ev) => {
      try {
        onUpdate(JSON.parse(ev.data))
      } catch {
        // ignore non-JSON frames
      }
    }
    return ws
  },
  listRules() {
    return http.get<ScreenerRulesCatalog>('/screeners/rules').then(r => r.data)
  },
}
