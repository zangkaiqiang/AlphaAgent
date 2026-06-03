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

      <!-- ── AI 研究报告 ───────────────────────────────────────────── -->
      <div class="aa-card report-card">
        <div class="card-accent-bar report-accent-bar" />
        <div class="card-header">
          <span class="card-title">AI 研究报告</span>
          <el-button type="primary" :loading="agentLoading" @click="runAgent" size="small">
            生成研究报告
          </el-button>
        </div>
        <div class="card-body">

          <!-- ── loading state ─────────────────────────────────────── -->
          <template v-if="agentLoading">
            <p class="report-loading-hint aa-muted">
              <span class="report-loading-dot" />
              智能体正在获取财报与资讯并撰写报告…
            </p>
            <el-skeleton :rows="7" animated />
          </template>

          <!-- ── empty state ───────────────────────────────────────── -->
          <el-empty
            v-else-if="!agent"
            description="点击「生成研究报告」让 AI 综合技术面、财务与资讯给出研判"
          />

          <!-- ── report body ───────────────────────────────────────── -->
          <div v-else class="report-body">

            <!-- ┌ Hero: rating + confidence ┐ -->
            <div class="report-hero" :class="`report-hero--${agent.rating.toLowerCase()}`">
              <div class="report-hero-left">
                <div class="report-rating-badge" :class="`rating-${agent.rating.toLowerCase()}`">
                  {{ ratingLabel(agent.rating) }}
                </div>
                <div class="report-rating-en aa-muted">{{ agent.rating }}</div>
              </div>
              <div class="report-hero-right">
                <div v-if="agent.confidence != null" class="report-confidence">
                  <span class="report-confidence-label aa-muted">置信度</span>
                  <span class="report-confidence-value aa-num">
                    {{ Math.round(agent.confidence * 100) }}%
                  </span>
                  <div class="report-confidence-bar">
                    <div
                      class="report-confidence-fill"
                      :class="`rating-${agent.rating.toLowerCase()}`"
                      :style="{ width: `${Math.round(agent.confidence * 100)}%` }"
                    />
                  </div>
                </div>
                <div class="report-meta-tags">
                  <el-tag v-if="!agent.data_complete" type="warning" size="small" effect="plain">
                    资讯不完整
                  </el-tag>
                  <span class="report-model-tag aa-muted">{{ agent.model }}</span>
                </div>
              </div>
            </div>

            <!-- notes (small muted lines) -->
            <div v-if="agent.notes && agent.notes.length" class="report-notes">
              <p v-for="(n, i) in agent.notes" :key="i" class="report-note aa-muted">
                <span class="report-note-bullet">›</span> {{ n }}
              </p>
            </div>

            <!-- ┌ Sections with inline [n] citations ┐ -->
            <div class="report-sections">
              <div
                v-for="(sec, si) in agent.sections"
                :key="si"
                class="report-section"
              >
                <h3 class="report-section-title">{{ sec.title }}</h3>
                <div class="report-section-body">
                  <template v-for="(para, pi) in splitParas(sec.body)" :key="pi">
                    <p class="report-para">
                      <template v-for="(chunk, ci) in parseCitations(para)" :key="ci">
                        <a
                          v-if="chunk.type === 'cite'"
                          class="cite"
                          @click.prevent="goSource(chunk.id!)"
                          :title="`来源 [${chunk.id}]`"
                        >[{{ chunk.id }}]</a>
                        <span v-else>{{ chunk.text }}</span>
                      </template>
                    </p>
                  </template>
                </div>
              </div>
            </div>

            <!-- ┌ Sources panel ┐ -->
            <div v-if="agent.sources && agent.sources.length" class="report-sources">
              <div class="report-sources-header">
                <span class="report-sources-title">来源</span>
                <span class="report-sources-count aa-muted">{{ agent.sources.length }} 条</span>
              </div>
              <div class="report-sources-list">
                <div
                  v-for="s in agent.sources"
                  :key="s.id"
                  :id="`src-${s.id}`"
                  class="report-source-item"
                  :class="`source-type--${s.type}`"
                >
                  <div class="source-id-badge">[{{ s.id }}]</div>
                  <div class="source-content">
                    <div class="source-label">{{ s.label }}</div>
                    <!-- financial detail -->
                    <template v-if="s.type === 'financial'">
                      <div class="source-detail-row">
                        <template v-for="(v, k) in s.detail" :key="k">
                          <span class="source-kv">
                            <span class="source-k aa-muted">{{ k }}</span>
                            <span class="source-v aa-num">{{ v }}</span>
                          </span>
                        </template>
                      </div>
                    </template>
                    <!-- news detail -->
                    <template v-else-if="s.type === 'news'">
                      <div class="source-detail-row source-news-meta aa-muted">
                        <span v-if="s.detail.date">{{ s.detail.date }}</span>
                        <span v-if="s.detail.source">· {{ s.detail.source }}</span>
                        <a
                          v-if="s.detail.url"
                          :href="String(s.detail.url)"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="source-ext-link"
                        >↗ 原文</a>
                      </div>
                    </template>
                    <!-- technical detail -->
                    <template v-else-if="s.type === 'technical'">
                      <div class="source-detail-row">
                        <template v-for="(v, k) in s.detail" :key="k">
                          <span class="source-kv">
                            <span class="source-k aa-muted">{{ k }}</span>
                            <span class="source-v aa-num">{{ v }}</span>
                          </span>
                        </template>
                      </div>
                    </template>
                    <!-- fallback: any other type -->
                    <template v-else>
                      <div class="source-detail-row">
                        <template v-for="(v, k) in s.detail" :key="k">
                          <span class="source-kv">
                            <span class="source-k aa-muted">{{ k }}</span>
                            <span class="source-v">{{ v }}</span>
                          </span>
                        </template>
                      </div>
                    </template>
                  </div>
                  <div class="source-type-pill">{{ s.type }}</div>
                </div>
              </div>
            </div>

            <!-- disclaimer -->
            <div v-if="agent.disclaimer" class="report-disclaimer aa-muted">
              {{ agent.disclaimer }}
            </div>
          </div><!-- /report-body -->
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
import type { ResearchReport } from '@/api/types'
import { useSessionStore } from '@/stores/session'
import SymbolPicker from '@/components/common/SymbolPicker.vue'
import KLineChart from '@/components/chart/KLineChart.vue'
import StatCard from '@/components/common/StatCard.vue'

const session = useSessionStore()
const form = reactive({ symbol: session.symbol })
const overview = ref<CompanyOverview | null>(null)
const loading = ref(false)

const agent = ref<ResearchReport | null>(null)
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

const ratingLabel = (r: string): string =>
  ({ BUY: '买入', SELL: '卖出', HOLD: '持有', UNKNOWN: '数据不足' } as Record<string, string>)[r] ?? r

// ── Citation parsing ──────────────────────────────────────────────
interface TextChunk { type: 'text'; text: string }
interface CiteChunk { type: 'cite'; id: number }
type Chunk = TextChunk | CiteChunk

/** Split body text into plain text runs and [n] citation markers. */
function parseCitations(text: string): Chunk[] {
  const result: Chunk[] = []
  const parts = text.split(/(\[\d+\])/)
  for (const part of parts) {
    const m = part.match(/^\[(\d+)\]$/)
    if (m) {
      result.push({ type: 'cite', id: parseInt(m[1], 10) })
    } else if (part) {
      result.push({ type: 'text', text: part })
    }
  }
  return result
}

/** Split body into paragraphs on newline boundaries. */
function splitParas(body: string): string[] {
  return body.split('\n').filter(p => p.trim().length > 0)
}

/** Scroll source anchor into view and flash highlight. */
function goSource(id: number) {
  const el = document.getElementById(`src-${id}`)
  if (!el) return
  el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  el.classList.add('source-flash')
  setTimeout(() => el.classList.remove('source-flash'), 1200)
}

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

/* ── Report card ─────────────────────────────────────────────────── */
.report-accent-bar {
  background: linear-gradient(180deg, var(--aa-accent) 0%, transparent 100%);
}

/* loading hint */
.report-loading-hint {
  display: flex;
  align-items: center;
  gap: var(--aa-2);
  font-size: 13px;
  margin-bottom: var(--aa-3);
}
.report-loading-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--aa-accent);
  animation: report-pulse 1.4s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes report-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

/* ── Hero block ─────────────────────────────────────────────────── */
.report-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--aa-4);
  padding: var(--aa-4) var(--aa-5);
  border-radius: var(--aa-radius-sm);
  margin-bottom: var(--aa-4);
  background: var(--aa-surface-2);
  border: 1px solid var(--aa-border);
  flex-wrap: wrap;
}

/* Hero tint by rating */
.report-hero--buy  { border-color: rgba(245, 69, 92, 0.3);  background: rgba(245, 69, 92, 0.05); }
.report-hero--sell { border-color: rgba(39, 192, 138, 0.3); background: rgba(39, 192, 138, 0.05); }
.report-hero--hold { border-color: rgba(240, 180, 41, 0.3); background: rgba(240, 180, 41, 0.05); }
.report-hero--unknown { border-color: var(--aa-border); }

.report-hero-left {
  display: flex;
  align-items: center;
  gap: var(--aa-3);
}

/* Rating badge */
.report-rating-badge {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1;
}
.rating-buy     { color: var(--aa-pos); }
.rating-sell    { color: var(--aa-neg); }
.rating-hold    { color: var(--aa-accent); }
.rating-unknown { color: var(--aa-text-muted); }

.report-rating-en {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 2px;
}

/* Confidence */
.report-hero-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--aa-2);
}
.report-confidence {
  display: flex;
  align-items: center;
  gap: var(--aa-2);
  flex-wrap: wrap;
  justify-content: flex-end;
}
.report-confidence-label { font-size: 12px; }
.report-confidence-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--aa-text);
}
.report-confidence-bar {
  width: 100px;
  height: 4px;
  border-radius: 2px;
  background: var(--aa-border-strong);
  overflow: hidden;
}
.report-confidence-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}
.report-confidence-fill.rating-buy     { background: var(--aa-pos); }
.report-confidence-fill.rating-sell    { background: var(--aa-neg); }
.report-confidence-fill.rating-hold    { background: var(--aa-accent); }
.report-confidence-fill.rating-unknown { background: var(--aa-border-strong); }

.report-meta-tags {
  display: flex;
  align-items: center;
  gap: var(--aa-2);
  flex-wrap: wrap;
}
.report-model-tag {
  font-size: 10px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  padding: 2px 6px;
  border-radius: var(--aa-radius-sm);
  background: var(--aa-surface-2);
  border: 1px solid var(--aa-border);
}

/* ── Notes ──────────────────────────────────────────────────────── */
.report-notes {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: var(--aa-4);
}
.report-note {
  font-size: 12px;
  line-height: 1.6;
  margin: 0;
}
.report-note-bullet {
  margin-right: 4px;
  opacity: 0.5;
}

/* ── Report sections ─────────────────────────────────────────────── */
.report-sections {
  display: flex;
  flex-direction: column;
  gap: var(--aa-4);
  margin-bottom: var(--aa-5);
}
.report-section {
  border-left: 2px solid var(--aa-border-strong);
  padding-left: var(--aa-4);
}
.report-section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--aa-accent);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0 0 var(--aa-2);
}
.report-section-body .report-para {
  margin: 0 0 8px;
  font-size: 14px;
  line-height: 1.75;
  color: var(--aa-text);
}
.report-section-body .report-para:last-child { margin-bottom: 0; }

/* Inline citation anchors */
.cite {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--aa-accent);
  background: rgba(240, 180, 41, 0.12);
  border: 1px solid rgba(240, 180, 41, 0.3);
  border-radius: 3px;
  padding: 0 4px;
  margin: 0 1px;
  line-height: 1.5;
  cursor: pointer;
  text-decoration: none;
  vertical-align: baseline;
  transition: background 0.15s, border-color 0.15s;
}
.cite:hover {
  background: rgba(240, 180, 41, 0.25);
  border-color: rgba(240, 180, 41, 0.6);
  color: var(--aa-accent);
}

/* ── Sources panel ───────────────────────────────────────────────── */
.report-sources {
  margin-bottom: var(--aa-4);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius-sm);
  overflow: hidden;
}
.report-sources-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--aa-2) var(--aa-4);
  background: var(--aa-surface-2);
  border-bottom: 1px solid var(--aa-border);
}
.report-sources-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--aa-text-muted);
}
.report-sources-count { font-size: 11px; }

.report-sources-list {
  display: flex;
  flex-direction: column;
}
.report-source-item {
  display: flex;
  align-items: flex-start;
  gap: var(--aa-3);
  padding: var(--aa-3) var(--aa-4);
  border-bottom: 1px solid var(--aa-border);
  transition: background 0.2s;
}
.report-source-item:last-child { border-bottom: none; }
.report-source-item:hover { background: var(--aa-surface-2); }

/* Flash highlight on goSource() */
.source-flash {
  background: rgba(240, 180, 41, 0.12) !important;
  transition: background 0.05s;
}

/* Source type color accents */
.source-type--financial .source-id-badge { color: var(--aa-accent); border-color: rgba(240, 180, 41, 0.4); }
.source-type--news      .source-id-badge { color: var(--aa-pos);    border-color: rgba(245, 69, 92, 0.4); }
.source-type--technical .source-id-badge { color: var(--aa-neg);    border-color: rgba(39, 192, 138, 0.4); }

.source-id-badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  width: 30px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--aa-border-strong);
  border-radius: 3px;
  margin-top: 1px;
}
.source-content {
  flex: 1;
  min-width: 0;
}
.source-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--aa-text);
  margin-bottom: 3px;
}
.source-detail-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px var(--aa-3);
}
.source-kv {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.source-k { font-size: 11px; }
.source-v { font-variant-numeric: tabular-nums; }
.source-news-meta {
  font-size: 12px;
  gap: var(--aa-2);
}
.source-ext-link {
  color: var(--aa-accent);
  text-decoration: none;
  font-size: 12px;
}
.source-ext-link:hover { text-decoration: underline; }

.source-type-pill {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--aa-text-muted);
  padding: 2px 6px;
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius-sm);
  align-self: flex-start;
  margin-top: 1px;
}

/* ── Disclaimer ─────────────────────────────────────────────────── */
.report-disclaimer {
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
