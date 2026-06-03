import * as echarts from 'echarts/core'

// A-share convention: 涨=红 (--aa-pos), 跌=绿 (--aa-neg).
// NOTE: hex kept literal here (echarts theme can't read CSS vars); keep in sync with theme.css.
export const AA_DARK = 'aa-dark'

echarts.registerTheme(AA_DARK, {
  backgroundColor: 'transparent',
  textStyle: { color: '#8b97a7' },
  title: { textStyle: { color: '#e6edf3' } },
  legend: { textStyle: { color: '#8b97a7' } },
  grid: { borderColor: '#26303c' },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#33404f' } },
    splitLine: { lineStyle: { color: '#1b2230' } },
    axisLabel: { color: '#8b97a7' },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: '#33404f' } },
    splitLine: { lineStyle: { color: '#1b2230' } },
    axisLabel: { color: '#8b97a7' },
  },
  candlestick: {
    itemStyle: { color: '#f5455c', color0: '#27c08a', borderColor: '#f5455c', borderColor0: '#27c08a' },
  },
  color: ['#f0b429', '#5aa9e6', '#27c08a', '#f5455c', '#b48ead'],
})
