<template>
  <div class="page">
    <el-card shadow="never" class="search">
      <SymbolPicker v-model="form.symbol" @submit="load" />
    </el-card>

    <el-empty v-if="!overview && !loading" description="输入股票代码后点查询" />
    <el-skeleton v-if="loading" :rows="6" animated />

    <template v-if="overview">
      <el-card shadow="never" class="header">
        <div class="header-row">
          <div>
            <div class="title">{{ overview.info.name }} <span class="muted">{{ overview.info.symbol }}</span></div>
            <div class="sub">
              {{ overview.info.industry || '行业未知' }}
              <span v-if="overview.info.listed_date"> · 上市于 {{ overview.info.listed_date }}</span>
            </div>
          </div>
          <el-descriptions :column="3" border size="small" class="kpis">
            <el-descriptions-item label="总市值">{{ fmtCap(overview.info.market_cap) }}</el-descriptions-item>
            <el-descriptions-item label="流通市值">{{ fmtCap(overview.info.float_market_cap) }}</el-descriptions-item>
            <el-descriptions-item label="PE">{{ fmtNum(overview.info.pe) }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div class="returns">
          <el-tag
            v-for="(v, k) in overview.returns"
            :key="k"
            :type="v >= 0 ? 'danger' : 'success'"
            effect="plain"
            size="large"
          >
            {{ k }}: {{ (v * 100).toFixed(2) }}%
          </el-tag>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>K 线 + 均线 + 成交量</template>
        <KLineChart :kline="overview.kline" />
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <span>AI 智能分析</span>
            <el-button type="primary" :loading="agentLoading" @click="runAgent">运行分析</el-button>
          </div>
        </template>
        <el-empty v-if="!agent" description="点击「运行分析」让 AI 综合技术面与财务给出研判" />
        <div v-else>
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <el-tag :type="ratingType(agent.rating)" size="large">{{ ratingLabel(agent.rating) }}</el-tag>
            <span v-if="agent.confidence != null">置信度 {{ Math.round(agent.confidence * 100) }}%</span>
            <el-tag v-if="agent.data_complete === false" type="warning" size="small">数据不完整</el-tag>
          </div>
          <p style="margin-bottom:12px">{{ agent.summary }}</p>
          <el-row :gutter="16">
            <el-col :span="12">
              <strong>看多 / 支撑</strong>
              <ul><li v-for="(r, i) in agent.reasons" :key="i">{{ r }}</li></ul>
            </el-col>
            <el-col :span="12">
              <strong>风险点</strong>
              <ul><li v-for="(r, i) in agent.risks" :key="i">{{ r }}</li></ul>
            </el-col>
          </el-row>
          <el-alert v-if="agent.disclaimer" :title="agent.disclaimer" type="info" :closable="false" style="margin-top:12px" />
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>财务指标</template>
        <el-table :data="overview.financials" stripe size="small">
          <el-table-column prop="period" label="期间" width="120" />
          <el-table-column label="ROE" align="right">
            <template #default="{ row }">{{ fmtPct(row.roe) }}</template>
          </el-table-column>
          <el-table-column label="毛利率" align="right">
            <template #default="{ row }">{{ fmtPct(row.gross_margin) }}</template>
          </el-table-column>
          <el-table-column label="净利率" align="right">
            <template #default="{ row }">{{ fmtPct(row.net_margin) }}</template>
          </el-table-column>
          <el-table-column label="营收" align="right">
            <template #default="{ row }">{{ fmtCap(row.revenue) }}</template>
          </el-table-column>
          <el-table-column label="营收同比" align="right">
            <template #default="{ row }">
              <span :class="pctClass(row.revenue_yoy)">{{ fmtPct(row.revenue_yoy) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="净利润" align="right">
            <template #default="{ row }">{{ fmtCap(row.net_income) }}</template>
          </el-table-column>
          <el-table-column label="净利同比" align="right">
            <template #default="{ row }">
              <span :class="pctClass(row.net_income_yoy)">{{ fmtPct(row.net_income_yoy) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="资产负债率" align="right">
            <template #default="{ row }">{{ fmtPct(row.debt_ratio) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
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
  return v >= 0 ? 'pos' : 'neg'
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.search { max-width: 540px; }
.header-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.title { font-size: 22px; font-weight: 600; }
.muted { color: #6b7280; font-weight: normal; font-size: 14px; margin-left: 6px; }
.sub { color: #6b7280; margin-top: 4px; }
.kpis { min-width: 480px; }
.returns { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.pos { color: #dc2626; font-weight: 600; }
.neg { color: #16a34a; font-weight: 600; }
</style>
