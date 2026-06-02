<template>
  <div class="page">
    <el-skeleton v-if="loading" :rows="6" animated />
    <template v-else-if="snap">
      <!-- indices row -->
      <div class="indices">
        <el-card v-for="idx in snap.indices" :key="idx.code" shadow="never" class="idx-card">
          <div class="idx-name">{{ idx.name }} <span class="muted">{{ idx.code }}</span></div>
          <div class="idx-last" :class="idx.change_pct >= 0 ? 'pos' : 'neg'">
            {{ idx.last.toFixed(2) }}
          </div>
          <div :class="idx.change_pct >= 0 ? 'pos' : 'neg'">
            {{ idx.change_pct >= 0 ? '+' : '' }}{{ idx.change_pct.toFixed(2) }}%
          </div>
        </el-card>
      </div>

      <!-- breadth + northbound -->
      <div class="two-cols">
        <el-card shadow="never">
          <template #header>市场宽度</template>
          <div class="breadth">
            <div class="breadth-bars">
              <el-tooltip :content="`上涨 ${snap.breadth.advancers}`">
                <div class="bar pos-bg" :style="{ flex: snap.breadth.advancers ?? 0 }">
                  <span v-if="(snap.breadth.advancers ?? 0) > 0">{{ snap.breadth.advancers }}</span>
                </div>
              </el-tooltip>
              <el-tooltip :content="`平盘 ${snap.breadth.unchanged}`">
                <div class="bar neutral-bg" :style="{ flex: snap.breadth.unchanged ?? 0 }">
                  <span v-if="(snap.breadth.unchanged ?? 0) > 0">{{ snap.breadth.unchanged }}</span>
                </div>
              </el-tooltip>
              <el-tooltip :content="`下跌 ${snap.breadth.decliners}`">
                <div class="bar neg-bg" :style="{ flex: snap.breadth.decliners ?? 0 }">
                  <span v-if="(snap.breadth.decliners ?? 0) > 0">{{ snap.breadth.decliners }}</span>
                </div>
              </el-tooltip>
            </div>
            <el-descriptions :column="3" border size="small" style="margin-top: 16px;">
              <el-descriptions-item label="上涨">
                <span class="pos">{{ snap.breadth.advancers ?? '—' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="下跌">
                <span class="neg">{{ snap.breadth.decliners ?? '—' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="平盘">{{ snap.breadth.unchanged ?? '—' }}</el-descriptions-item>
              <el-descriptions-item label="涨停">
                <span class="pos">{{ snap.breadth.limit_up ?? '—' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="跌停">
                <span class="neg">{{ snap.breadth.limit_down ?? '—' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="多空比">
                {{ snap.breadth.advance_decline_ratio?.toFixed(2) ?? '—' }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>北向资金</template>
          <div class="northbound">
            <div class="big" :class="(snap.northbound_net ?? 0) >= 0 ? 'pos' : 'neg'">
              {{ fmtFlow(snap.northbound_net) }}
            </div>
            <div class="muted">沪深港通当日净流入</div>
          </div>
        </el-card>
      </div>
    </template>
    <el-empty v-else description="未获取到大盘数据" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { analysisApi, type MarketSnapshot } from '@/api/analysis'

const snap = ref<MarketSnapshot | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    snap.value = await analysisApi.marketSnapshot()
  } finally {
    loading.value = false
  }
}

onMounted(load)

function fmtFlow(v: number | null) {
  if (v == null) return '—'
  const abs = Math.abs(v)
  if (abs >= 1e8) return `${(v / 1e8).toFixed(2)} 亿`
  if (abs >= 1e4) return `${(v / 1e4).toFixed(2)} 万`
  return v.toFixed(2)
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.indices {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.idx-card {
  text-align: center;
  padding: 4px 0;
}
.idx-name {
  font-size: 14px;
  margin-bottom: 6px;
}
.idx-last {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}
.muted { color: #6b7280; font-size: 12px; font-weight: normal; }
.two-cols {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}
.breadth-bars {
  display: flex;
  height: 32px;
  border-radius: 4px;
  overflow: hidden;
}
.bar {
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 13px;
  font-weight: 600;
  transition: flex 0.3s;
}
.pos-bg { background: #dc2626; }
.neutral-bg { background: #9ca3af; }
.neg-bg { background: #16a34a; }
.pos { color: #dc2626; font-weight: 600; }
.neg { color: #16a34a; font-weight: 600; }
.northbound { text-align: center; padding: 16px 0; }
.big { font-size: 32px; font-weight: 700; }
</style>
