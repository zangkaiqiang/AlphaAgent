<template>
  <div class="page">

    <!-- ── Search ──────────────────────────────────────────────────── -->
    <div class="search-wrap">
      <SymbolPicker v-model="form.symbol" @submit="load" />
    </div>

    <el-empty v-if="!overview && !loading" description="输入股票代码后点查询" />
    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-if="overview">

      <!-- ── Company header ─────────────────────────────────────────── -->
      <div class="aa-card header-card">
        <div class="card-accent-bar" />
        <div class="header-inner">
          <!-- identity -->
          <div class="company-identity">
            <div class="company-name">
              {{ overview.info.name }}
              <span class="aa-muted symbol-tag">{{ overview.info.symbol }}</span>
            </div>
            <div class="company-sub aa-muted">
              {{ overview.info.industry || '行业未知' }}
              <span v-if="overview.info.listed_date"> · 上市于 {{ overview.info.listed_date }}</span>
            </div>
          </div>

          <!-- KPI stat row -->
          <div class="kpi-row">
            <StatCard label="总市值" :value="fmtCap(overview.info.market_cap)" />
            <StatCard label="流通市值" :value="fmtCap(overview.info.float_market_cap)" />
            <StatCard label="市盈率 PE" :value="fmtNum(overview.info.pe)" />
          </div>
        </div>

        <!-- multi-window return tags (红涨绿跌) -->
        <div class="returns-row">
          <template v-for="(v, k) in overview.returns" :key="k">
            <span class="return-tag" :class="v >= 0 ? 'return-pos' : 'return-neg'">
              <span class="return-key aa-muted">{{ k }}</span>
              <span class="return-val aa-num">{{ (v * 100).toFixed(2) }}%</span>
            </span>
          </template>
        </div>
      </div>

      <!-- ── K-line chart ───────────────────────────────────────────── -->
      <div class="aa-card">
        <div class="card-accent-bar" />
        <div class="card-header">
          <span class="card-title">K 线 + 均线 + 成交量</span>
        </div>
        <div class="card-body">
          <KLineChart :kline="overview.kline" />
        </div>
      </div>

      <!-- ── AI 研判 ─────────────────────────────────────────────────── -->
      <!-- SP2: replace with cited research-report viewer -->
      <div class="aa-card ai-card">
        <div class="card-accent-bar" />
        <div class="card-header">
          <span class="card-title">AI 智能分析</span>
          <el-button type="primary" :loading="agentLoading" @click="runAgent" size="small">
            运行分析
          </el-button>
        </div>
        <div class="card-body">
          <!-- skeleton while loading -->
          <el-skeleton v-if="agentLoading" :rows="5" animated />

          <el-empty
            v-else-if="!agent"
            description="点击「运行分析」让 AI 综合技术面与财务给出研判"
          />

          <div v-else class="ai-result">
            <!-- rating + confidence row -->
            <div class="ai-meta-row">
              <el-tag :type="ratingType(agent.rating)" size="large" effect="dark">
                {{ ratingLabel(agent.rating) }}
              </el-tag>
              <span v-if="agent.confidence != null" class="confidence aa-muted aa-num">
                置信度&nbsp;<strong class="aa-text">{{ Math.round(agent.confidence * 100) }}%</strong>
              </span>
              <el-tag v-if="agent.data_complete === false" type="warning" size="small">
                数据不完整
              </el-tag>
            </div>

            <!-- summary -->
            <p class="ai-summary">{{ agent.summary }}</p>

            <!-- reasons / risks -->
            <div class="ai-columns">
              <div class="ai-col">
                <div class="ai-col-header pos-label">看多 / 支撑</div>
                <ul class="reason-list">
                  <li v-for="(r, i) in agent.reasons" :key="i">{{ r }}</li>
                </ul>
              </div>
              <div class="ai-col">
                <div class="ai-col-header neg-label">风险点</div>
                <ul class="reason-list reason-list--risks">
                  <li v-for="(r, i) in agent.risks" :key="i">{{ r }}</li>
                </ul>
              </div>
            </div>

            <!-- disclaimer -->
            <div v-if="agent.disclaimer" class="ai-disclaimer aa-muted">
              {{ agent.disclaimer }}
            </div>
          </div>
        </div>
      </div>

      <!-- ── Financials table ───────────────────────────────────────── -->
      <div class="aa-card">
        <div class="card-accent-bar" />
        <div class="card-header">
          <span class="card-title">财务指标</span>
        </div>
        <div class="card-body card-body--table">
          <el-table
            :data="overview.financials"
            size="small"
            class="fin-table"
          >
            <el-table-column prop="period" label="期间" width="120" />
            <el-table-column label="ROE" align="right">
              <template #default="{ row }">
                <span class="aa-num" :class="pctClass(row.roe)">{{ fmtPct(row.roe) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="毛利率" align="right">
              <template #default="{ row }">
                <span class="aa-num">{{ fmtPct(row.gross_margin) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="净利率" align="right">
              <template #default="{ row }">
                <span class="aa-num">{{ fmtPct(row.net_margin) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="营收" align="right">
              <template #default="{ row }">
                <span class="aa-num">{{ fmtCap(row.revenue) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="营收同比" align="right">
              <template #default="{ row }">
                <span class="aa-num" :class="pctClass(row.revenue_yoy)">{{ fmtPct(row.revenue_yoy) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="净利润" align="right">
              <template #default="{ row }">
                <span class="aa-num">{{ fmtCap(row.net_income) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="净利同比" align="right">
              <template #default="{ row }">
                <span class="aa-num" :class="pctClass(row.net_income_yoy)">{{ fmtPct(row.net_income_yoy) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="资产负债率" align="right">
              <template #default="{ row }">
                <span class="aa-num">{{ fmtPct(row.debt_ratio) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { analysisApi, type CompanyOverview } from '@/api/analysis'
import type { CompanyAnalysis } from '@/api/types'
import { useSessionStore } from '@/stores/session'
import SymbolPicker from '@/components/common/SymbolPicker.vue'
import KLineChart from '@/components/chart/KLineChart.vue'
import StatCard from '@/components/common/StatCard.vue'

const session = useSessionStore()
const form = reactive({ symbol: session.symbol })
const overview = ref<CompanyOverview | null>(null)
const loading = ref(false)

const agent = ref<CompanyAnalysis | null>(null)
const agentLoading = ref(false)

async function load() {
  if (!form.symbol) return
  session.setSymbol(form.symbol)
  agent.value = null
  loading.value = true
  try {
    overview.value = await analysisApi.companyOverview(form.symbol)
  } catch {
    overview.value = null
  } finally {
    loading.value = false
  }
}

async function runAgent() {
  if (!form.symbol) return
  agentLoading.value = true
  try {
    agent.value = await analysisApi.agentAnalyze(form.symbol)
  } catch {
    // axios interceptor already showed the error via ElMessage
  } finally {
    agentLoading.value = false
  }
}

const ratingType = (r: string): string =>
  ({ BUY: 'success', SELL: 'danger', HOLD: 'info' } as Record<string, string>)[r] ?? 'warning'
const ratingLabel = (r: string): string =>
  ({ BUY: '买入', SELL: '卖出', HOLD: '持有', UNKNOWN: '数据不足' } as Record<string, string>)[r] ?? r

onMounted(load)

function fmtNum(v: number | null) {
  return v == null ? '—' : v.toFixed(2)
}
function fmtPct(v: number | null) {
  if (v == null) return '—'
  const pct = Math.abs(v) <= 1 ? v * 100 : v
  return `${pct.toFixed(2)}%`
}
function fmtCap(v: number | null) {
  if (v == null) return '—'
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)} 亿`
  if (v >= 1e4) return `${(v / 1e4).toFixed(2)} 万`
  return v.toFixed(2)
}
function pctClass(v: number | null) {
  if (v == null) return ''
  return v >= 0 ? 'aa-pos' : 'aa-neg'
}
</script>

<style scoped>
/* ── Page layout ──────────────────────────────────────────────────── */
.page {
  display: flex;
  flex-direction: column;
  gap: var(--aa-4);
  padding-bottom: var(--aa-6);
}

/* ── Search wrapper ───────────────────────────────────────────────── */
.search-wrap {
  background: var(--aa-surface);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius);
  padding: var(--aa-4);
  max-width: 560px;
}

/* ── Base card ────────────────────────────────────────────────────── */
.aa-card {
  position: relative;
  background: var(--aa-surface);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius);
  box-shadow: var(--aa-shadow);
  overflow: hidden;
}

/* left accent bar — consistent across all cards */
.card-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  width: 2px;
  height: 100%;
  background: var(--aa-accent);
  border-radius: var(--aa-radius) 0 0 var(--aa-radius);
}

/* ── Card header ──────────────────────────────────────────────────── */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--aa-3) var(--aa-4) var(--aa-3) calc(var(--aa-4) + 10px);
  border-bottom: 1px solid var(--aa-border);
}
.card-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--aa-text);
  text-transform: uppercase;
}
.card-body {
  padding: var(--aa-4) var(--aa-4) var(--aa-4) calc(var(--aa-4) + 10px);
}
.card-body--table {
  padding: 0 0 0 0; /* table owns its own spacing */
  overflow-x: auto;
}

/* ── Header card ─────────────────────────────────────────────────── */
.header-inner {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--aa-4);
  padding: var(--aa-4) var(--aa-4) var(--aa-3) calc(var(--aa-4) + 10px);
  flex-wrap: wrap;
}
.company-name {
  font-size: 22px;
  font-weight: 700;
  color: var(--aa-text);
  line-height: 1.25;
}
.symbol-tag {
  font-size: 13px;
  font-weight: 400;
  margin-left: var(--aa-2);
  font-variant-numeric: tabular-nums;
}
.company-sub {
  margin-top: var(--aa-1);
  font-size: 13px;
}

/* KPI stat row */
.kpi-row {
  display: flex;
  gap: var(--aa-2);
  flex-wrap: wrap;
}

/* return tags */
.returns-row {
  display: flex;
  gap: var(--aa-2);
  flex-wrap: wrap;
  padding: var(--aa-3) var(--aa-4) var(--aa-4) calc(var(--aa-4) + 10px);
  border-top: 1px solid var(--aa-border);
}
.return-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: var(--aa-radius-sm);
  font-size: 12px;
  border: 1px solid transparent;
}
.return-pos {
  color: var(--aa-pos);
  background: rgba(245, 69, 92, 0.08);
  border-color: rgba(245, 69, 92, 0.22);
}
.return-neg {
  color: var(--aa-neg);
  background: rgba(39, 192, 138, 0.08);
  border-color: rgba(39, 192, 138, 0.22);
}
.return-key {
  font-size: 11px;
}
.return-val {
  font-weight: 600;
}

/* ── AI section ─────────────────────────────────────────────────── */
.ai-meta-row {
  display: flex;
  align-items: center;
  gap: var(--aa-3);
  margin-bottom: var(--aa-3);
  flex-wrap: wrap;
}
.confidence {
  font-size: 13px;
}
.ai-summary {
  margin: 0 0 var(--aa-4);
  line-height: 1.7;
  color: var(--aa-text);
  font-size: 14px;
}
.ai-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--aa-4);
  margin-bottom: var(--aa-4);
}
@media (max-width: 640px) {
  .ai-columns { grid-template-columns: 1fr; }
}
.ai-col-header {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--aa-2);
  padding-bottom: var(--aa-1);
  border-bottom: 1px solid var(--aa-border);
}
.pos-label { color: var(--aa-pos); border-bottom-color: rgba(245, 69, 92, 0.3); }
.neg-label { color: var(--aa-neg); border-bottom-color: rgba(39, 192, 138, 0.3); }

.reason-list {
  margin: 0;
  padding-left: var(--aa-4);
  color: var(--aa-text);
  font-size: 13px;
  line-height: 1.8;
}
.reason-list--risks li::marker { color: var(--aa-neg); }
.reason-list:not(.reason-list--risks) li::marker { color: var(--aa-pos); }

.ai-disclaimer {
  font-size: 11px;
  line-height: 1.6;
  padding: var(--aa-2) var(--aa-3);
  background: var(--aa-surface-2);
  border-radius: var(--aa-radius-sm);
  border-left: 2px solid var(--aa-border-strong);
}

/* ── Financials table overrides ─────────────────────────────────── */
.fin-table :deep(.el-table__header-wrapper th) {
  background: var(--aa-surface-2) !important;
  color: var(--aa-text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
}
.fin-table :deep(.el-table__row) {
  background: var(--aa-surface);
}
.fin-table :deep(.el-table__row:hover > td) {
  background: var(--aa-surface-2) !important;
}
.fin-table :deep(td) {
  border-bottom: 1px solid var(--aa-border) !important;
}
</style>
