<template>
  <div ref="el" class="echart"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EquityPoint } from '@/api/types'

echarts.use([
  LineChart,
  GridComponent,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
])

const props = defineProps<{
  curve: EquityPoint[]
  byStrategy?: Record<string, EquityPoint[]>
}>()

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function dedupe(points: EquityPoint[]): [string, number][] {
  // Portfolio writes one snapshot per symbol per bar; keep the last per timestamp.
  const map = new Map<string, number>()
  for (const p of points) map.set(p.timestamp, p.equity)
  return [...map.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1))
}

function computeDrawdown(rows: [string, number][]): [string, number][] {
  let peak = -Infinity
  return rows.map(([t, v]) => {
    peak = Math.max(peak, v)
    return [t, peak > 0 ? (v / peak - 1) * 100 : 0]
  })
}

function render() {
  if (!chart || !props.curve?.length) return
  const main = dedupe(props.curve)
  const dd = computeDrawdown(main)

  const series: any[] = [
    {
      name: '净值',
      type: 'line',
      showSymbol: false,
      data: main,
      smooth: true,
      lineStyle: { width: 2 },
    },
    {
      name: '回撤 (%)',
      type: 'line',
      yAxisIndex: 1,
      showSymbol: false,
      data: dd,
      areaStyle: { opacity: 0.15 },
      lineStyle: { width: 1, color: '#ef4444' },
      itemStyle: { color: '#ef4444' },
    },
  ]

  if (props.byStrategy) {
    for (const [sid, curve] of Object.entries(props.byStrategy)) {
      series.push({
        name: sid,
        type: 'line',
        showSymbol: false,
        data: dedupe(curve),
        lineStyle: { width: 1, type: 'dashed' },
      })
    }
  }

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { left: 60, right: 60, top: 40, bottom: 60 },
    xAxis: { type: 'time' },
    yAxis: [
      { type: 'value', scale: true, name: '净值' },
      { type: 'value', name: '回撤 %', max: 0, axisLabel: { formatter: '{value}%' } },
    ],
    dataZoom: [
      { type: 'inside' },
      { type: 'slider', height: 20 },
    ],
    series,
  })
}

onMounted(() => {
  chart = echarts.init(el.value!)
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

function resize() {
  chart?.resize()
}

watch(() => [props.curve, props.byStrategy], () => render(), { deep: true })
</script>

<style scoped>
.echart {
  width: 100%;
  height: 420px;
}
</style>
