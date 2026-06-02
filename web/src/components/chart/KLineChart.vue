<template>
  <div ref="el" class="echart"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { KLinePoint } from '@/api/analysis'

echarts.use([
  CandlestickChart,
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer,
])

const props = defineProps<{ kline: KLinePoint[] }>()
const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function calcMA(closes: number[], n: number): (number | null)[] {
  const out: (number | null)[] = []
  for (let i = 0; i < closes.length; i++) {
    if (i < n - 1) {
      out.push(null)
      continue
    }
    let sum = 0
    for (let j = i - n + 1; j <= i; j++) sum += closes[j]
    out.push(sum / n)
  }
  return out
}

function render() {
  if (!chart || !props.kline.length) return
  const dates = props.kline.map(k => k.timestamp)
  // ECharts candlestick expects [open, close, low, high]
  const ohlc = props.kline.map(k => [k.open, k.close, k.low, k.high])
  const closes = props.kline.map(k => k.close)
  const volumes = props.kline.map(k => k.volume)

  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 0 },
    grid: [
      { left: 60, right: 30, top: 40, height: '60%' },
      { left: 60, right: 30, top: '78%', height: '15%' },
    ],
    xAxis: [
      { type: 'category', data: dates, boundaryGap: false, axisLine: { onZero: false } },
      { type: 'category', gridIndex: 1, data: dates, boundaryGap: false, axisLine: { onZero: false }, axisLabel: { show: false } },
    ],
    yAxis: [
      { scale: true, splitArea: { show: true } },
      { gridIndex: 1, scale: true, axisLabel: { show: false } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], top: '95%', height: 18, start: 50, end: 100 },
    ],
    series: [
      {
        name: 'K 线',
        type: 'candlestick',
        data: ohlc,
        itemStyle: {
          color: '#dc2626',         // 红涨
          color0: '#16a34a',        // 绿跌
          borderColor: '#dc2626',
          borderColor0: '#16a34a',
        },
      },
      {
        name: 'MA5',
        type: 'line',
        data: calcMA(closes, 5),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#fbbf24' },
      },
      {
        name: 'MA20',
        type: 'line',
        data: calcMA(closes, 20),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#3b82f6' },
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: { color: '#9ca3af' },
      },
    ],
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

watch(() => props.kline, () => render(), { deep: true })
</script>

<style scoped>
.echart {
  width: 100%;
  height: 480px;
}
</style>
