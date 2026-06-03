<template>
  <div class="grid">
    <!-- ===== Left: config form ===== -->
    <el-card class="card form-card" shadow="never">
      <template #header><span>回测配置</span></template>

      <el-form :model="form" label-position="top" size="default">
        <el-form-item label="标签(可选)">
          <el-input v-model="form.label" placeholder="给这次回测起个名字" />
        </el-form-item>

        <el-divider content-position="left">数据</el-divider>
        <el-form-item label="数据源">
          <el-select v-model="form.dataSource" style="width: 100%">
            <el-option label="本地 CSV" value="csv" />
            <el-option label="AkShare(免费)" value="akshare" />
            <el-option label="Tushare(需 token)" value="tushare" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.dataSource === 'csv'" label="CSV 目录">
          <el-input v-model="form.dataRoot" placeholder="例如 ./data" />
        </el-form-item>
        <el-form-item label="股票代码(每行一个)">
          <el-input v-model="form.symbolsText" type="textarea" :rows="4" placeholder="600000&#10;000001" />
        </el-form-item>
        <el-form-item label="时间区间">
          <el-date-picker
            v-model="form.range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="K 线周期">
          <el-select v-model="form.freq" style="width: 100%">
            <el-option label="日线" value="1d" />
            <el-option label="60 分钟" value="60m" />
            <el-option label="30 分钟" value="30m" />
            <el-option label="15 分钟" value="15m" />
            <el-option label="5 分钟" value="5m" />
            <el-option label="1 分钟" value="1m" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">策略</el-divider>
        <el-form-item label="策略">
          <el-select v-model="form.strategy" style="width: 100%" @change="syncDefaultParams">
            <el-option
              v-for="s in strategiesStore.list"
              :key="s.name"
              :label="`${s.name}  —  ${s.class_name}`"
              :value="s.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-for="p in currentParams"
          :key="p.name"
          :label="`${p.name} (${p.type})`"
        >
          <el-input-number
            v-if="p.type === 'int' || p.type === 'float'"
            v-model="form.params[p.name]"
            :step="p.type === 'float' ? 0.1 : 1"
            :precision="p.type === 'float' ? 2 : 0"
            style="width: 100%"
          />
          <el-input v-else v-model="form.params[p.name]" />
        </el-form-item>

        <el-divider content-position="left">组合</el-divider>
        <el-form-item label="初始资金">
          <el-input-number v-model="form.initialCash" :min="10000" :step="100000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单次仓位比例 (target_pct)">
          <el-slider v-model="form.targetPct" :min="0.05" :max="1" :step="0.05" />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :icon="VideoPlay"
            :loading="job?.status === 'running'"
            @click="submit"
            class="action-button"
          >
            {{ job?.status === 'running' ? '回测中…' : '运行回测' }}
          </el-button>
          <el-button
            v-if="job?.status === 'running'"
            :icon="Close"
            @click="cancel"
            class="action-button secondary-action"
          >
            取消
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- ===== Right: results ===== -->
    <div class="results">
      <el-card v-if="job" class="card" shadow="never">
        <template #header>
          <div class="job-header">
            <span>任务 {{ job.id.slice(0, 8) }} <el-tag :type="statusType">{{ statusLabel }}</el-tag></span>
            <span class="muted">{{ job.bars_processed }} / {{ job.bars_total }} bars · {{ job.fill_count }} 成交</span>
          </div>
        </template>
        <el-progress :percentage="Math.round((job.progress || 0) * 100)" :status="progressStatus" />
        <el-alert v-if="job.error" type="error" :title="job.error" :closable="false" style="margin-top: 8px;" />
      </el-card>

      <el-card v-if="result" class="card" shadow="never">
        <template #header><span>净值曲线</span></template>
        <EquityChart :curve="result.equity_curve" :by-strategy="result.equity_by_strategy" />
      </el-card>

      <el-card v-if="result" class="card" shadow="never">
        <template #header><span>绩效指标</span></template>
        <MetricsTable :perf="result.performance" />
      </el-card>

      <el-card v-if="result && result.fills.length" class="card" shadow="never">
        <template #header><span>成交明细({{ result.fills.length }})</span></template>
        <FillsTable :fills="result.fills" />
      </el-card>

      <el-empty v-if="!job && !result" class="empty-state" description="左侧填好配置后点击「运行回测」" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, VideoPlay } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { backtestApi } from '@/api/backtest'
import type { BacktestResult, JobInfo, StrategyInfo } from '@/api/types'
import { useStrategiesStore } from '@/stores/strategies'
import EquityChart from '@/components/chart/EquityChart.vue'
import MetricsTable from '@/components/MetricsTable.vue'
import FillsTable from '@/components/FillsTable.vue'

const strategiesStore = useStrategiesStore()

const form = reactive({
  label: '',
  dataSource: 'csv',
  dataRoot: './data',
  symbolsText: '600000\n000001',
  range: [
    dayjs().subtract(1, 'year').format('YYYY-MM-DD'),
    dayjs().format('YYYY-MM-DD'),
  ] as [string, string],
  freq: '1d',
  strategy: 'ma_cross',
  params: {} as Record<string, unknown>,
  initialCash: 1_000_000,
  targetPct: 0.3,
})

const currentParams = computed(() => {
  const s = strategiesStore.list.find(x => x.name === form.strategy)
  return s?.params || []
})

function syncDefaultParams() {
  const strat = strategiesStore.list.find(s => s.name === form.strategy)
  if (!strat) return
  const next: Record<string, unknown> = {}
  for (const p of strat.params) {
    next[p.name] = (form.params as Record<string, unknown>)[p.name] ?? p.default
  }
  form.params = next
}

onMounted(async () => {
  await strategiesStore.load()
  syncDefaultParams()
})

watch(() => strategiesStore.list, () => syncDefaultParams(), { once: true })

const job = ref<JobInfo | null>(null)
const result = ref<BacktestResult | null>(null)
let ws: WebSocket | null = null

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[job.value?.status || ''] || ''
})

const statusType = computed(() => {
  const map: Record<string, 'info' | 'success' | 'danger' | 'warning'> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[job.value?.status || 'info']
})

const progressStatus = computed(() => {
  if (job.value?.status === 'completed') return 'success'
  if (job.value?.status === 'failed') return 'exception'
  return undefined
})

function buildConfig(): Record<string, unknown> {
  const symbols = form.symbolsText
    .split('\n')
    .map(s => s.trim())
    .filter(Boolean)

  const dataCfg: Record<string, unknown> = {
    source: form.dataSource,
    symbols,
    start: form.range[0],
    end: form.range[1],
    freq: form.freq,
  }
  if (form.dataSource === 'csv') dataCfg.root = form.dataRoot

  return {
    data: dataCfg,
    strategy: {
      name: form.strategy,
      params: form.params,
    },
    portfolio: {
      initial_cash: form.initialCash,
      target_pct: form.targetPct,
    },
  }
}

async function submit() {
  result.value = null
  closeWs()
  try {
    const { job_id } = await backtestApi.submit({
      config: buildConfig(),
      label: form.label || undefined,
    })
    job.value = await backtestApi.get(job_id)
    ws = backtestApi.watch(job_id, async info => {
      job.value = info
      if (info.status === 'completed') {
        result.value = await backtestApi.result(info.id)
        ElMessage.success('回测完成')
      }
      if (info.status === 'failed') ElMessage.error(info.error || '回测失败')
    })
  } catch (e) {
    console.error(e)
  }
}

async function cancel() {
  if (!job.value) return
  await backtestApi.cancel(job.value.id)
}

function closeWs() {
  ws?.close()
  ws = null
}

onBeforeUnmount(closeWs)
</script>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: minmax(320px, 360px) minmax(0, 1fr);
  gap: var(--aa-5);
  align-items: start;
  min-height: 100%;
}
.form-card {
  height: max-content;
  position: sticky;
  top: 0;
  max-height: calc(100vh - 106px);
}
.form-card :deep(.el-card__body) {
  max-height: calc(100vh - 156px);
  overflow-y: auto;
}
.results {
  display: flex;
  flex-direction: column;
  gap: var(--aa-4);
  min-width: 0;
}
.card :deep(.el-card__header) {
  padding: var(--aa-3) var(--aa-4);
  font-weight: 600;
}
.job-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--aa-3);
  flex-wrap: wrap;
}
.job-header > span:first-child {
  display: inline-flex;
  align-items: center;
  gap: var(--aa-2);
}
.muted {
  color: var(--aa-text-muted);
  font-weight: normal;
  font-size: 13px;
}
.action-button {
  width: 100%;
}
.secondary-action {
  margin-top: var(--aa-2);
}
.empty-state {
  min-height: min(520px, calc(100vh - 128px));
}
:deep(.el-divider) {
  margin: 18px 0 14px;
}

@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .form-card {
    position: static;
    max-height: none;
  }

  .form-card :deep(.el-card__body) {
    max-height: none;
  }
}
</style>
