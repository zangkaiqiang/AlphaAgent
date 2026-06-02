<template>
  <el-container class="app-shell">
    <el-aside width="220px" class="sidebar">
      <div class="brand">
        <el-icon :size="22"><Aim /></el-icon>
        <span>AlphaAgent</span>
      </div>
      <el-menu :default-active="route.path" router class="menu">
        <template v-for="(group, section) in grouped" :key="section">
          <div class="section">{{ section }}</div>
          <el-menu-item
            v-for="item in group"
            :key="item.path"
            :index="item.path"
            :disabled="item.enabled === false"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>
              <span>{{ item.title }}</span>
              <el-tag v-if="item.enabled === false" size="small" type="info" effect="plain" round>
                即将
              </el-tag>
            </template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="title">{{ currentTitle }}</div>
        <div class="actions">
          <el-link :underline="false" href="/api/docs" target="_blank">API 文档</el-link>
        </div>
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { routes } from '@/router'

const route = useRoute()

type NavItem = {
  path: string
  title: string
  icon: string
  section: string
  enabled?: boolean
}

const items = computed<NavItem[]>(() => {
  const root = routes.find(r => r.path === '/')
  if (!root || !root.children) return []
  return root.children.map(c => ({
    path: '/' + c.path,
    title: (c.meta?.title as string) || c.path,
    icon: (c.meta?.icon as string) || 'Document',
    section: (c.meta?.section as string) || '其他',
    enabled: c.meta?.enabled !== false,
  }))
})

const grouped = computed(() => {
  const out: Record<string, NavItem[]> = {}
  for (const it of items.value) {
    ;(out[it.section] ||= []).push(it)
  }
  return out
})

const currentTitle = computed(() => {
  const found = items.value.find(it => it.path === route.path)
  return found?.title || ''
})
</script>

<style scoped>
.app-shell {
  height: 100vh;
}
.sidebar {
  background: #1f2937;
  color: #e5e7eb;
  overflow-y: auto;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 20px;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #374151;
}
.menu {
  background: #1f2937;
  border-right: none;
}
.section {
  padding: 14px 20px 6px;
  font-size: 12px;
  color: #9ca3af;
  letter-spacing: 0.05em;
}
:deep(.el-menu) {
  --el-menu-bg-color: #1f2937;
  --el-menu-text-color: #e5e7eb;
  --el-menu-hover-bg-color: #374151;
  --el-menu-active-color: #fbbf24;
  border-right: none;
}
:deep(.el-menu-item.is-disabled) {
  color: #6b7280 !important;
  cursor: not-allowed;
}
:deep(.el-menu-item .el-tag) {
  margin-left: 8px;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  padding: 0 24px;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.content {
  padding: 24px;
  background: #f3f4f6;
}
</style>
