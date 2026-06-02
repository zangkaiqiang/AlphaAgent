<template>
  <div class="grid">
    <!-- ===== Left: config form ===== -->
    <el-card class="card form-card" shadow="never">
      <template #header><span>选股配置</span></template>

      <el-form :model="form" label-position="top" size="default">
        <el-form-item label="标签(可选)">
          <el-input v-model="form.label" placeholder="给这次选股起个名字" />
        </el-form-item>

        <el-divider content-position="left">股票池</el-divider>
        <el-form-item label="来源">
          <el-select v-model="form.universeSource" style="width: 100%">
            <el-option label="指数成分(AkShare)" value="akshare_index" />
            <el-option label="自定义列表" value="static" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.universeSource === 'akshare_index'" label="指数代码">
          <el-input v-model="form.indexCode" placeholder="例如 000300" />
        </el-form-item>
        <el-form-item v-else label="股票代码(每行一个)">
          <el-input v-model="form.symbolsText" type="textarea" :rows="4" placeholder="600000&#10;000001" />
        </el-form-item>

        <el-divider content-position="left">参数</el-divider>
        <el-form-item label="截止日期">
          <el-date-picker
            v-model="form.asOf"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="回看天数">
          <el-input-number v-model="form.lookbackDays" :min="10" :max="500" :step="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="输出 Top N">
          <el-input-number v-model="form.topN" :min="5" :max="200" :step="5" style="width: 100%" />
        </el-form-item>

        <el-divider content-position="left">过滤器</el-divider>
        <div v-if="catalog">
          <div v-for="f in catalog.filters" :key="f.type" class="rule-row">
            <el-checkbox v-model="selectedFilters[f.type]">
              {{ f.type }}
              <span class="muted"> — {{ f.class_name }}</span>
            </el-checkbox>
          </div>
          <el-empty v-if="catalog.filters.length === 0" description="暂无过滤器" :image-size="40" />
        </div>
        <el-skeleton v-else :rows="2" animated />

        <el-divider content-position="left">规则 & 权重</el-divider>
        <div v-if="catalog">
          <div v-for="r in catalog.rules" :key="r.type" class="rule-row">
            <el-checkbox v-model="selectedRules[r.type]" style="flex: 1; min-width: 0;">
              <span class="rule-label">{{ r.type }}</span>
              <span class="muted"> {{ r.category }}</span>
            </el-checkbox>
            <el-input-number
              v-if="selectedRules[r.type]"
              v-model="ruleWeights[r.type]"
              :min="0"
              :max="10"
              :step="0.5"
              :precision="1"
              size="small"
              style="width: 90px; margin-left: 8px;"
            />
          </div>
          <el-empty v-if="catalog.rules.length === 0" description="暂无规则" :image-size="40" />
        </div>
        <el-skeleton v-else :rows="3" animated />

        <el-form-item style="margin-top: 16px;">
          <el-button
            type="primary"
            :loading="job?.status === 'running' || job?.status === 'pending'"
            @click="submit"
            style="width: 100%"
          >
            {{ job?.status === 'running' || job?.status === 'pending' ? '选股中…' : '运行选股' }}
          </el-button>
          <el-button
            v-if="job?.status === 'running' || job?.status === 'pending'"
            @click="cancel"
            style="width: 100%; margin-top: 8px;"
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
            <span class="muted">
              {{ job.picks_count !== null ? `${job.picks_count} 只` : '' }}
            </span>
          </div>
        </template>
        <el-progress :percentage="Math.round((job.progress || 0) * 100)" :status="progressStatus" />
        <el-alert v-if="job.error" type="error" :title="job.error" :closable="false" style="margin-top: 8px;" />
      </el-card>

      <el-card v-if="screenResult" class="card" shadow="never">
        <template #header>
          <div class="job-header">
            <span>选股结果 ({{ screenResult.picks.length }} 只)</span>
            <span class="muted">
              {{ screenResult.universe_name }} · 股票池 {{ screenResult.universe_size }} →
              过滤后 {{ screenResult.filtered_size }}
            </span>
          </div>
        </template>
        <el-table
          :data="screenResult.picks"
          stripe
          style="width: 100%"
        >
          <el-table-column type="index" label="#" width="60" />
          <el-table-column prop="symbol" label="代码" width="100" />
          <el-table-column prop="name" label="名称" width="140" />
          <el-table-column label="综合评分" width="120">
            <template #default="{ row }: { row: ScreenPick }">
              {{ row.final_score.toFixed(4) }}
            </template>
          </el-table-column>
          <el-table-column label="规则得分明细" type="expand">
            <template #default="{ row }: { row: ScreenPick }">
              <div class="reasons-panel">
                <el-table :data="row.reasons" size="small" :show-header="true">
                  <el-table-column prop="rule_name" label="规则" width="180" />
                  <el-table-column label="得分" width="100">
                    <template #default="{ row: r }: { row: ScreenPickReason }">
                      {{ r.score.toFixed(4) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="详情">
                    <template #default="{ row: r }: { row: ScreenPickReason }">
                      <span class="detail-text">{{ JSON.stringify(r.detail) }}</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-empty v-if="!job && !screenResult" description="左侧填好配置后点击「运行选股」" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { screenerApi } from '@/api/screener'
import type { ScreenerJobInfo, ScreenResult, ScreenerRulesCatalog, ScreenPick, ScreenPickReason } from '@/api/types'

const form = reactive({
  label: '',
  universeSource: 'akshare_index' as 'akshare_index' | 'static',
  indexCode: '000300',
  symbolsText: '600000\n000001',
  asOf: dayjs().format('YYYY-MM-DD'),
  lookbackDays: 120,
  topN: 30,
})

const catalog = ref<ScreenerRulesCatalog | null>(null)
const selectedRules = reactive<Record<string, boolean>>({})
const ruleWeights = reactive<Record<string, number>>({})
const selectedFilters = reactive<Record<string, boolean>>({})

onMounted(async () => {
  try {
    catalog.value = await screenerApi.listRules()
    // Pre-select first rule if any and set default weights
    if (catalog.value) {
      for (const r of catalog.value.rules) {
        selectedRules[r.type] = false
        ruleWeights[r.type] = 1.0
      }
      for (const f of catalog.value.filters) {
        selectedFilters[f.type] = false
      }
    }
  } catch (e) {
    console.error('Failed to load screener rules', e)
  }
})

const job = ref<ScreenerJobInfo | null>(null)
const screenResult = ref<ScreenResult | null>(null)
let ws: WebSocket | null = null

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    completed: '完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[job.value?.status ?? ''] ?? ''
})

const statusType = computed((): 'info' | 'success' | 'danger' | 'warning' => {
  const map: Record<string, 'info' | 'success' | 'danger' | 'warning'> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[job.value?.status ?? ''] ?? 'info'
})

const progressStatus = computed(() => {
  if (job.value?.status === 'completed') return 'success'
  if (job.value?.status === 'failed') return 'exception'
  return undefined
})

function buildConfig(): Record<string, unknown> {
  const universe: Record<string, unknown> =
    form.universeSource === 'akshare_index'
      ? { source: 'akshare_index', index_code: form.indexCode }
      : {
          source: 'static',
          symbols: form.symbolsText
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean),
        }

  const filters = Object.entries(selectedFilters)
    .filter(([, checked]) => checked)
    .map(([type]) => ({ type }))

  const rules = Object.entries(selectedRules)
    .filter(([, checked]) => checked)
    .map(([type]) => ({ type, weight: ruleWeights[type] ?? 1.0 }))

  return {
    universe,
    data: {
      source: 'akshare',
      adjust: 'qfq',
      cache_dir: './data/cache',
      freq: '1d',
    },
    meta: { source: 'akshare' },
    as_of: form.asOf,
    lookback_days: form.lookbackDays,
    calendar_enabled: true,
    filters,
    rules,
    output: { top_n: form.topN },
  }
}

async function submit() {
  screenResult.value = null
  closeWs()
  try {
    const { job_id } = await screenerApi.submit({
      config: buildConfig(),
      label: form.label || undefined,
    })
    job.value = await screenerApi.get(job_id)
    ws = screenerApi.watch(job_id, async (info) => {
      job.value = info
      if (info.status === 'completed') {
        screenResult.value = await screenerApi.result(info.id)
        ElMessage.success('选股完成')
      }
      if (info.status === 'failed') ElMessage.error(info.error ?? '选股失败')
    })
  } catch (e) {
    console.error(e)
  }
}

async function cancel() {
  if (!job.value) return
  await screenerApi.cancel(job.value.id)
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
  grid-template-columns: 380px 1fr;
  gap: 16px;
  height: 100%;
}
.form-card {
  height: max-content;
  position: sticky;
  top: 0;
}
.results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card :deep(.el-card__header) {
  padding: 12px 16px;
  font-weight: 600;
}
.job-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.muted {
  color: #6b7280;
  font-weight: normal;
  font-size: 13px;
}
.rule-row {
  display: flex;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #f3f4f6;
}
.rule-label {
  font-size: 13px;
}
.reasons-panel {
  padding: 8px 16px;
}
.detail-text {
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
}
</style>
