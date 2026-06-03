import * as echarts from 'echarts/core'

// A-share convention: 涨=红 (--aa-pos), 跌=绿 (--aa-neg).
// NOTE: hex kept literal here (echarts theme can't read CSS vars); keep in sync with theme.css.
export const AA_DARK = 'aa-dark'

echarts.registerTheme(AA_DARK, {
  backgroundColor: 'transparent',
  textStyle: { color: '#95a39b' },
  title: { textStyle: { color: '#edf2ee' } },
  legend: { textStyle: { color: '#95a39b' } },
  grid: { borderColor: '#28342f' },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#3a4a43' } },
    splitLine: { lineStyle: { color: '#1d2421' } },
    axisLabel: { color: '#95a39b' },
  },
  valueAxis: {
    axisLine: { lineStyle: { color: '#3a4a43' } },
    splitLine: { lineStyle: { color: '#1d2421' } },
    axisLabel: { color: '#95a39b' },
  },
  candlestick: {
    itemStyle: { color: '#f05a68', color0: '#25c38a', borderColor: '#f05a68', borderColor0: '#25c38a' },
  },
  color: ['#d9a93a', '#67b7dc', '#25c38a', '#f05a68', '#c188d2'],
})
