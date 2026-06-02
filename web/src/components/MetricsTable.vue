<template>
  <el-descriptions :column="3" border>
    <el-descriptions-item v-for="m in items" :key="m.label" :label="m.label">
      <span :class="m.cls">{{ m.value }}</span>
    </el-descriptions-item>
  </el-descriptions>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PerformanceDTO } from '@/api/types'

const props = defineProps<{ perf: PerformanceDTO }>()

function pct(x: number, digits = 2): string {
  return `${(x * 100).toFixed(digits)}%`
}

function num(x: number, digits = 2): string {
  if (!isFinite(x)) return '∞'
  return x.toFixed(digits)
}

const items = computed(() => {
  const p = props.perf
  return [
    { label: '总收益率', value: pct(p.total_return), cls: p.total_return >= 0 ? 'pos' : 'neg' },
    { label: '年化收益', value: pct(p.annualized_return), cls: p.annualized_return >= 0 ? 'pos' : 'neg' },
    { label: '年化波动', value: pct(p.annualized_volatility) },
    { label: 'Sharpe', value: num(p.sharpe), cls: p.sharpe >= 1 ? 'pos' : '' },
    { label: 'Sortino', value: num(p.sortino) },
    { label: '最大回撤', value: pct(p.max_drawdown), cls: 'neg' },
    { label: 'Calmar', value: num(p.calmar) },
    { label: '交易次数', value: p.trades.toString() },
    { label: '胜率', value: pct(p.win_rate) },
    { label: '平均盈利', value: num(p.avg_win), cls: 'pos' },
    { label: '平均亏损', value: num(p.avg_loss), cls: 'neg' },
    { label: '盈利因子', value: num(p.profit_factor) },
    { label: '总盈亏', value: num(p.total_pnl), cls: p.total_pnl >= 0 ? 'pos' : 'neg' },
  ]
})
</script>

<style scoped>
.pos {
  color: #dc2626;
  font-weight: 600;
}
.neg {
  color: #16a34a;
  font-weight: 600;
}
</style>
