<template>
  <el-container class="app-shell">
    <el-aside width="220px" class="sidebar">
      <!-- Brand area -->
      <div class="brand">
        <div class="brand-mark">
          <el-icon :size="16"><Aim /></el-icon>
        </div>
        <div class="brand-text">
          <span class="brand-name">AlphaAgent</span>
          <span class="brand-tagline">量化交易终端</span>
        </div>
      </div>

      <!-- Navigation -->
      <el-menu :default-active="route.path" router class="menu">
        <template v-for="(group, section) in grouped" :key="section">
          <div class="section-header">
            <span>{{ section }}</span>
          </div>
          <el-menu-item
            v-for="item in group"
            :key="item.path"
            :index="item.path"
            :disabled="item.enabled === false"
            class="nav-item"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>
              <span class="nav-label">{{ item.title }}</span>
              <el-tag
                v-if="item.enabled === false"
                size="small"
                type="info"
                effect="plain"
                round
                class="coming-tag"
              >
                即将
              </el-tag>
            </template>
          </el-menu-item>
        </template>
      </el-menu>

      <!-- Sidebar footer -->
      <div class="sidebar-footer">
        <span class="version-label">v0.1.0-alpha</span>
      </div>
    </el-aside>

    <el-container class="main-container">
      <el-header class="topbar" height="52px">
        <div class="topbar-left">
          <div class="page-section">{{ currentSection }}</div>
          <div class="topbar-sep">/</div>
          <div class="page-title">{{ currentTitle }}</div>
        </div>
        <div class="topbar-right">
          <el-link :underline="false" href="/api/docs" target="_blank" class="api-link">
            <el-icon class="api-icon"><Document /></el-icon>
            API 文档
          </el-link>
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

const currentSection = computed(() => {
  const found = items.value.find(it => it.path === route.path)
  return found?.section || ''
})
</script>

<style scoped>
/* ─── Layout shell ─────────────────────────────────────────────── */
.app-shell {
  height: 100vh;
  background: var(--aa-bg);
  overflow: hidden;
}

/* ─── Sidebar ───────────────────────────────────────────────────── */
.sidebar {
  display: flex;
  flex-direction: column;
  background: var(--aa-surface);
  border-right: 1px solid var(--aa-border);
  overflow: hidden;
  box-shadow: 1px 0 0 var(--aa-border);
  /* subtle inner right shadow for depth */
  filter: drop-shadow(2px 0 8px rgba(0, 0, 0, 0.32));
}

/* Brand area */
.brand {
  display: flex;
  align-items: center;
  gap: var(--aa-3);
  padding: var(--aa-5) var(--aa-4);
  border-bottom: 1px solid var(--aa-border);
  /* subtle accent glow behind the mark */
  position: relative;
}

.brand::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    var(--aa-accent) 0%,
    transparent 60%
  );
  opacity: 0.5;
}

.brand-mark {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--aa-accent) 0%, rgba(240, 180, 41, 0.6) 100%);
  border-radius: var(--aa-radius-sm);
  color: #0b0e14;
  flex-shrink: 0;
  box-shadow: 0 0 12px rgba(240, 180, 41, 0.3);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--aa-text);
  letter-spacing: 0.01em;
  line-height: 1.2;
  white-space: nowrap;
}

.brand-tagline {
  font-size: 10px;
  color: var(--aa-text-muted);
  letter-spacing: 0.08em;
  line-height: 1.2;
  white-space: nowrap;
}

/* Navigation menu */
.menu {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--aa-2) 0;
  /* Remove Element Plus border */
  border-right: none !important;
}

/* Scrollbar inside sidebar */
.menu::-webkit-scrollbar {
  width: 4px;
}
.menu::-webkit-scrollbar-thumb {
  background: var(--aa-border-strong);
  border-radius: 4px;
}
.menu::-webkit-scrollbar-track {
  background: transparent;
}

/* Section group headers */
.section-header {
  padding: var(--aa-4) var(--aa-4) var(--aa-1);
  margin-top: var(--aa-2);
}

.section-header span {
  font-size: 10px;
  font-weight: 600;
  color: var(--aa-text-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.7;
}

/* Override El Menu variables */
:deep(.el-menu) {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: var(--aa-text-muted);
  --el-menu-hover-bg-color: var(--aa-surface-2);
  --el-menu-active-color: var(--aa-text);
  --el-menu-item-height: 40px;
  border-right: none !important;
}

/* Nav items */
:deep(.el-menu-item) {
  margin: 1px var(--aa-2);
  border-radius: var(--aa-radius-sm);
  height: 40px;
  line-height: 40px;
  padding-left: var(--aa-4) !important;
  color: var(--aa-text-muted);
  position: relative;
  transition: background 150ms ease, color 150ms ease;
  overflow: hidden;
}

:deep(.el-menu-item:hover) {
  background: var(--aa-surface-2) !important;
  color: var(--aa-text) !important;
}

/* Active state: left accent bar + surface highlight */
:deep(.el-menu-item.is-active) {
  background: var(--aa-surface-2) !important;
  color: var(--aa-text) !important;
}

:deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  background: var(--aa-accent);
  border-radius: 0 2px 2px 0;
  box-shadow: 0 0 8px rgba(240, 180, 41, 0.5);
}

/* Icon in nav items */
:deep(.el-menu-item .el-icon) {
  font-size: 15px;
  margin-right: var(--aa-2);
  transition: color 150ms ease;
}

/* Disabled items */
:deep(.el-menu-item.is-disabled) {
  opacity: 1 !important;
  color: var(--aa-border-strong) !important;
  cursor: not-allowed;
}

:deep(.el-menu-item.is-disabled .el-icon) {
  color: var(--aa-border-strong) !important;
}

/* Nav label */
.nav-label {
  flex: 1;
  font-size: 13.5px;
}

/* "即将" coming-soon tag */
.coming-tag {
  font-size: 10px;
  padding: 0 5px;
  height: 18px;
  line-height: 18px;
  border-color: var(--aa-border-strong) !important;
  color: var(--aa-border-strong) !important;
  background: transparent !important;
  margin-left: var(--aa-2);
}

/* Sidebar footer */
.sidebar-footer {
  padding: var(--aa-3) var(--aa-4);
  border-top: 1px solid var(--aa-border);
  margin-top: auto;
}

.version-label {
  font-size: 10px;
  color: var(--aa-border-strong);
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
}

/* ─── Main container ────────────────────────────────────────────── */
.main-container {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ─── Topbar ────────────────────────────────────────────────────── */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--aa-surface);
  border-bottom: 1px solid var(--aa-border);
  padding: 0 var(--aa-5);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--aa-2);
}

.page-section {
  font-size: 13px;
  color: var(--aa-text-muted);
  font-weight: 500;
}

.topbar-sep {
  font-size: 13px;
  color: var(--aa-border-strong);
  user-select: none;
}

.page-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--aa-text);
  letter-spacing: 0.01em;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--aa-3);
}

.api-link {
  font-size: 12.5px;
  color: var(--aa-text-muted) !important;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: color 150ms ease;
}

.api-link:hover {
  color: var(--aa-text) !important;
}

.api-icon {
  font-size: 13px;
}

/* ─── Content area ──────────────────────────────────────────────── */
.content {
  flex: 1;
  overflow-y: auto;
  background: var(--aa-bg);
  padding: var(--aa-5);
}
</style>
