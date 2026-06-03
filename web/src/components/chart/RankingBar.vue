<template>
  <div ref="el" class="echart" :style="{ height: height + 'px' }"></div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { AA_DARK } from '@/styles/echarts-dark'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = withDefaults(
  defineProps<{
    items: { label: string; value: number | null }[]
    formatter?: (v: number) => string
    color?: (v: number) => string
    height?: number
  }>(),
  { height: 400 },
)

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const colorFn = computed(() => props.color || ((v: number) => (v >= 0 ? '#f05a68' : '#25c38a')))
const fmt = computed(() => props.formatter || ((v: number) => v.toFixed(2)))

function render() {
  if (!chart) return
  const cleaned = props.items.filter(i => i.value !== null) as { label: string; value: number }[]
  const labels = cleaned.map(i => i.label)
  const values = cleaned.map(i => i.value)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 100, right: 60, top: 10, bottom: 30 },
    xAxis: { type: 'value', axisLabel: { formatter: (v: number) => fmt.value(v) } },
    yAxis: {
      type: 'category',
      data: labels,
      inverse: true,
      axisLabel: { fontSize: 12 },
    },
    series: [
      {
        type: 'bar',
        data: values.map(v => ({ value: v, itemStyle: { color: colorFn.value(v) } })),
        label: {
          show: true,
          position: 'right',
          formatter: (p: any) => fmt.value(p.value),
          fontSize: 11,
        },
      },
    ],
  })
}

onMounted(() => {
  chart = echarts.init(el.value!, AA_DARK)
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

watch(() => props.items, () => render(), { deep: true })
</script>

<style scoped>
.echart {
  width: 100%;
}
</style>
