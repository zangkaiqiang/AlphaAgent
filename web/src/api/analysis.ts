import http from './client'
import type { CompanyAnalysis } from './types'
export type { CompanyAnalysis }

// ---- Company ---------------------------------------------------------

export interface SecurityInfo {
  symbol: string
  name: string
  industry: string | null
  market_cap: number | null
  float_market_cap: number | null
  pe: number | null
  pb: number | null
  listed_date: string | null
}

export interface FinancialIndicators {
  period: string
  roe: number | null
  net_margin: number | null
  gross_margin: number | null
  revenue: number | null
  revenue_yoy: number | null
  net_income: number | null
  net_income_yoy: number | null
  debt_ratio: number | null
}

export interface KLinePoint {
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface CompanyOverview {
  info: SecurityInfo
  financials: FinancialIndicators[]
  kline: KLinePoint[]
  returns: Record<string, number>
}

// ---- Industry --------------------------------------------------------

export interface IndustrySummary {
  code: string
  name: string
  change_pct: number | null
  avg_pe: number | null
  constituent_count: number | null
  money_flow_net: number | null
}

export interface IndustryConstituent {
  symbol: string
  name: string
  change_pct: number | null
  market_cap: number | null
  pe: number | null
}

export interface IndustryDetail {
  industry: IndustrySummary
  constituents: IndustryConstituent[]
}

// ---- Market ----------------------------------------------------------

export interface MarketIndex {
  code: string
  name: string
  last: number
  change_pct: number
  volume: number | null
  amount: number | null
}

export interface MarketBreadth {
  as_of: string | null
  advancers: number | null
  decliners: number | null
  unchanged: number | null
  limit_up: number | null
  limit_down: number | null
  advance_decline_ratio: number | null
}

export interface MarketSnapshot {
  indices: MarketIndex[]
  breadth: MarketBreadth
  northbound_net: number | null
}

// ----------------------------------------------------------------------

export const analysisApi = {
  companyOverview: (symbol: string, days = 250) =>
    http.get<CompanyOverview>(`/analysis/company/${symbol}`, { params: { days } })
      .then(r => r.data),
  companyKline: (symbol: string, days = 180, freq = '1d') =>
    http.get<KLinePoint[]>(`/analysis/company/${symbol}/kline`, { params: { days, freq } })
      .then(r => r.data),

  industryList: (sort: 'change' | 'inflow' = 'change', descending = true) =>
    http.get<IndustrySummary[]>('/analysis/industry', { params: { sort, descending } })
      .then(r => r.data),
  industryDetail: (code: string) =>
    http.get<IndustryDetail>(`/analysis/industry/${code}`).then(r => r.data),

  marketSnapshot: () =>
    http.get<MarketSnapshot>('/analysis/market/snapshot').then(r => r.data),

  agentAnalyze: (symbol: string) =>
    http.post<CompanyAnalysis>(`/analysis/company/${symbol}/agent`).then(r => r.data),
  agentHistory: (symbol: string, limit = 10) =>
    http.get<CompanyAnalysis[]>(`/analysis/company/${symbol}/agent/history`, { params: { limit } }).then(r => r.data),
}
