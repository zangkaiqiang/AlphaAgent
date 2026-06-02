import http from './client'
import type { StrategyInfo } from './types'

export const strategiesApi = {
  list() {
    return http.get<StrategyInfo[]>('/strategies').then(r => r.data)
  },
}
