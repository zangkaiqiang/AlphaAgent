import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import AppLayout from '@/layouts/AppLayout.vue'

/**
 * Route metadata drives the sidebar.
 *
 *   meta.title        — Sidebar label (Chinese)
 *   meta.icon         — Element Plus icon component name
 *   meta.enabled      — false => visible but disabled (coming soon)
 *   meta.section      — Grouping label (separates top-level modules)
 *
 * Adding a new module = adding a route here + a page component. Sidebar
 * picks it up automatically.
 */
export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: AppLayout,
    redirect: '/backtest',
    children: [
      {
        path: 'backtest',
        name: 'backtest',
        component: () => import('@/pages/backtest/Index.vue'),
        meta: { title: '回测', icon: 'TrendCharts', section: '研究' },
      },
      {
        path: 'strategies',
        name: 'strategies',
        component: () => import('@/pages/strategies/Index.vue'),
        meta: { title: '策略库', icon: 'Collection', section: '研究' },
      },
      {
        path: 'screener',
        name: 'screener',
        component: () => import('@/pages/screener/Index.vue'),
        meta: { title: '选股', icon: 'Filter', section: '研究', enabled: false },
      },
      {
        path: 'analysis/company',
        name: 'analysis-company',
        component: () => import('@/pages/analysis/company/Index.vue'),
        meta: { title: '公司分析', icon: 'OfficeBuilding', section: '分析' },
      },
      {
        path: 'analysis/industry',
        name: 'analysis-industry',
        component: () => import('@/pages/analysis/industry/Index.vue'),
        meta: { title: '行业分析', icon: 'Histogram', section: '分析' },
      },
      {
        path: 'analysis/market',
        name: 'analysis-market',
        component: () => import('@/pages/analysis/market/Index.vue'),
        meta: { title: '大盘', icon: 'DataLine', section: '分析' },
      },
      {
        path: 'live',
        name: 'live',
        component: () => import('@/pages/live/Index.vue'),
        meta: { title: '实盘 / 模拟盘', icon: 'Monitor', section: '交易', enabled: false },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
