// Mirror the backend pydantic schemas. Keep in sync manually for now;
// can be auto-generated from OpenAPI later.

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface JobInfo {
  id: string
  label: string | null
  status: JobStatus
  progress: number
  bars_processed: number
  bars_total: number
  fill_count: number
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface EquityPoint {
  timestamp: string
  equity: number
}

export interface FillDTO {
  timestamp: string
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  fill_price: number
  commission: number
  stamp_tax: number
  order_id: string
  strategy_id: string
}

export interface PerformanceDTO {
  total_return: number
  annualized_return: number
  annualized_volatility: number
  sharpe: number
  sortino: number
  max_drawdown: number
  calmar: number
  trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  total_pnl: number
}

export interface BacktestResult {
  initial_cash: number
  final_equity: number
  total_return: number
  bars_processed: number
  bars_skipped: number
  fill_count: number
  cancelled: boolean
  equity_curve: EquityPoint[]
  fills: FillDTO[]
  performance: PerformanceDTO
  performance_by_strategy: Record<string, PerformanceDTO>
  equity_by_strategy: Record<string, EquityPoint[]>
}

export interface StrategyParam {
  name: string
  type: string
  default: unknown
  required: boolean
}

export interface StrategyInfo {
  name: string
  class_name: string
  description: string | null
  params: StrategyParam[]
}

// ── Screener types ──────────────────────────────────────────────────────────

export interface ScreenerJobInfo {
  id: string
  label: string | null
  status: JobStatus
  progress: number
  picks_count: number | null
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface ScreenPickReason {
  rule_name: string
  score: number
  detail: Record<string, unknown>
}

export interface ScreenPick {
  symbol: string
  name: string
  final_score: number
  reasons: ScreenPickReason[]
  metadata: Record<string, unknown>
}

export interface ScreenResult {
  generated_at: string
  resolved_as_of: string
  universe_name: string
  universe_size: number
  filtered_size: number
  rules_applied: string[]
  symbols: string[]
  picks: ScreenPick[]
}

export interface RuleParamInfo {
  name: string
  default: unknown
  required: boolean
}

export interface RuleInfo {
  type: string
  category: string
  class_name: string
  params: RuleParamInfo[]
}

export interface FilterInfo {
  type: string
  class_name: string
  params: RuleParamInfo[]
}

export interface ScreenerRulesCatalog {
  rules: RuleInfo[]
  filters: FilterInfo[]
}
