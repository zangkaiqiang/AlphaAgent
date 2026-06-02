<template>
  <div class="page">
    <div class="row">
      <el-card shadow="never" class="left">
        <template #header>
          <div class="card-header">
            <span>行业列表</span>
            <el-radio-group v-model="sort" size="small" @change="loadList">
              <el-radio-button label="change">按涨跌幅</el-radio-button>
              <el-radio-button label="inflow">按资金流入</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <el-skeleton v-if="loadingList" :rows="5" animated />
        <el-table
          v-else
          :data="industries"
          stripe
          size="small"
          @row-click="selectIndustry"
          highlight-current-row
          :row-class-name="rowClass"
        >
          <el-table-column prop="name" label="板块" width="120" />
          <el-table-column label="涨跌幅" align="right">
            <template #default="{ row }">
              <span :class="changeClass(row.change_pct)">{{ fmtPct(row.change_pct) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="主力净流入" align="right">
            <template #default="{ row }">{{ fmtCap(row.money_flow_net) }}</template>
          </el-table-column>
          <el-table-column prop="constituent_count" label="家数" align="right" width="80" />
        </el-table>
      </el-card>

      <el-card shadow="never" class="right">
        <template #header>
          {{ sort === 'change' ? '涨跌幅排名 (Top 20)' : '主力净流入 Top 20' }}
        </template>
        <RankingBar :items="rankItems" :formatter="rankFmt" :height="500" />
      </el-card>
    </div>

    <el-card v-if="detail" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ detail.industry.name }} · 成分股({{ detail.constituents.length }})</span>
          <el-tag :type="detail.industry.change_pct! >= 0 ? 'danger' : 'success'" effect="plain">
            {{ fmtPct(detail.industry.change_pct) }}
          </el-tag>
        </div>
      </template>
      <el-table :data="detail.constituents" stripe size="small" max-height="500">
        <el-table-column prop="symbol" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="140" />
        <el-table-column label="涨跌幅" align="right">
          <template #default="{ row }">
            <span :class="changeClass(row.change_pct)">{{ fmtPct(row.change_pct) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="总市值" align="right">
          <template #default="{ row }">{{ fmtCap(row.market_cap) }}</template>
        </el-table-column>
        <el-table-column label="PE" align="right">
          <template #default="{ row }">{{ row.pe != null ? row.pe.toFixed(2) : '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click.stop="gotoCompany(row.symbol)">查看</el-link>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { analysisApi, type IndustryDetail, type IndustrySummary } from '@/api/analysis'
import { useSessionStore } from '@/stores/session'
import RankingBar from '@/components/chart/RankingBar.vue'

const router = useRouter()
const session = useSessionStore()

const sort = ref<'change' | 'inflow'>('change')
const industries = ref<IndustrySummary[]>([])
const detail = ref<IndustryDetail | null>(null)
const loadingList = ref(false)

const rankItems = computed(() =>
  industries.value.slice(0, 20).map(i => ({
    label: i.name,
    value: sort.value === 'change' ? i.change_pct : i.money_flow_net,
  })),
)

const rankFmt = computed(() => {
  if (sort.value === 'change') return (v: number) => `${v.toFixed(2)}%`
  return (v: number) => {
    if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(1)} 亿`
    if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(1)} 万`
    return v.toFixed(0)
  }
})

async function loadList() {
  loadingList.value = true
  try {
    industries.value = await analysisApi.industryList(sort.value, true)
  } finally {
    loadingList.value = false
  }
}

async function selectIndustry(row: IndustrySummary) {
  detail.value = await analysisApi.industryDetail(row.code)
}

function gotoCompany(symbol: string) {
  session.setSymbol(symbol)
  router.push('/analysis/company')
}

onMounted(loadList)

// formatters
function fmtPct(v: number | null) {
  return v == null ? '—' : `${v.toFixed(2)}%`
}
function fmtCap(v: number | null) {
  if (v == null) return '—'
  if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(2)} 亿`
  if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(2)} 万`
  return v.toFixed(2)
}
function changeClass(v: number | null) {
  if (v == null) return ''
  return v >= 0 ? 'pos' : 'neg'
}
function rowClass({ row }: { row: IndustrySummary }) {
  return detail.value?.industry.code === row.code ? 'selected' : ''
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.row {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pos { color: #dc2626; font-weight: 600; }
.neg { color: #16a34a; font-weight: 600; }
:deep(.el-table .selected) { background: #fef3c7; }
</style>
