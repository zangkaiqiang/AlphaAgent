# 前端深色主题地基(SP1)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. **Implementers MUST also use the `frontend-design` skill** for the aesthetic component work (T2/T4/T5) to reach production-grade quality.

**Goal:** 把前端升级为统一的深色专业盘面(A股 红涨绿跌):全局设计 token + Element Plus 暗色 + 布局外壳 + echarts 深色 + 公司页/各页精修。

**Architecture:** 引入一层 CSS 变量 token(`web/src/styles/theme.css`)并覆盖 Element Plus 的 CSS 变量(启用其 dark 主题),使所有 EP 组件全局变深色;图表注册 echarts 暗色主题;组件用 token/class 取代裸 hex 与内联 style。不引入新框架(无 Tailwind)。

**Tech Stack:** Vue 3 + TypeScript + Element Plus 2.8(自带 dark 主题)+ ECharts 5.5 + Vite。**无前端单测**;每个任务的门槛是 `cd web && npm run build`(vue-tsc 类型检查 + vite 构建)通过,最终由用户目视验收。

**Spec:** `docs/superpowers/specs/2026-06-03-frontend-dark-theme-design.md`

---

## 文件结构

新增:
- `web/src/styles/theme.css` — 设计 token(CSS 变量)+ EP 暗色变量覆盖 + 基础样式。
- `web/src/styles/echarts-dark.ts` — echarts 暗色主题对象 + 注册。
- (可选)`web/src/components/common/StatCard.vue` — 统一 KPI/指标卡。

修改:
- `web/src/main.ts` — 引入 EP 暗色 css-vars + theme.css + `html.dark`。
- `web/src/layouts/AppLayout.vue` — 深色外壳。
- `web/src/components/chart/{KLineChart,EquityChart,RankingBar}.vue` — 应用暗色主题。
- `web/src/pages/analysis/company/Index.vue` — 公司页精修(AI 区仅主题化,报告查看器属 SP2)。
- `web/src/pages/{strategies,screener,analysis/industry,analysis/market,live}/Index.vue` — token 轻扫。

---

## Task 1: 设计 token + Element Plus 暗色(地基)

**Files:** Create `web/src/styles/theme.css`; Modify `web/src/main.ts`.

- [ ] **Step 1: Create `web/src/styles/theme.css`**

```css
:root {
  /* surfaces */
  --aa-bg: #0b0e14;
  --aa-surface: #141a23;
  --aa-surface-2: #1b2230;
  --aa-border: #26303c;
  --aa-border-strong: #33404f;
  /* text */
  --aa-text: #e6edf3;
  --aa-text-muted: #8b97a7;
  /* brand + semantics (A股 红涨绿跌) */
  --aa-accent: #f0b429;
  --aa-pos: #f5455c;   /* 涨 = 红 */
  --aa-neg: #27c08a;   /* 跌 = 绿 */
  /* shape */
  --aa-radius: 10px;
  --aa-radius-sm: 6px;
  --aa-shadow: 0 1px 0 rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.28);
  /* spacing scale */
  --aa-1: 4px; --aa-2: 8px; --aa-3: 12px; --aa-4: 16px; --aa-5: 24px; --aa-6: 32px;
}

/* Map Element Plus dark CSS variables onto our tokens so every EP component
   (card, table, tag, button, descriptions, menu) adopts the dark palette. */
html.dark {
  --el-bg-color: var(--aa-surface);
  --el-bg-color-overlay: var(--aa-surface-2);
  --el-bg-color-page: var(--aa-bg);
  --el-fill-color-blank: var(--aa-surface);
  --el-fill-color-light: var(--aa-surface-2);
  --el-border-color: var(--aa-border);
  --el-border-color-light: var(--aa-border);
  --el-border-color-lighter: var(--aa-border);
  --el-text-color-primary: var(--aa-text);
  --el-text-color-regular: var(--aa-text);
  --el-text-color-secondary: var(--aa-text-muted);
  --el-color-primary: var(--aa-accent);
  --el-color-danger: var(--aa-pos);    /* 红 = 涨 */
  --el-color-success: var(--aa-neg);   /* 绿 = 跌 */
}

html, body, #app { height: 100%; }
body {
  margin: 0;
  background: var(--aa-bg);
  color: var(--aa-text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
}
/* tabular numbers for financial figures */
.aa-num { font-variant-numeric: tabular-nums; }
.aa-pos { color: var(--aa-pos); }
.aa-neg { color: var(--aa-neg); }
.aa-muted { color: var(--aa-text-muted); }

/* subtle dark scrollbar */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: var(--aa-border-strong); border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }
```

- [ ] **Step 2: Wire it in `web/src/main.ts`** — add near the existing Element Plus import:

```typescript
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'   // EP dark variables
import '@/styles/theme.css'                            // our token overrides (import AFTER EP)
```
and after the app is created (before/after mount), enable dark mode:
```typescript
document.documentElement.classList.add('dark')
```
(Ensure `theme.css` is imported AFTER `element-plus/theme-chalk/dark/css-vars.css` so our overrides win.)

- [ ] **Step 3: Build gate**

Run: `cd web && npm run build`
Expected: passes (vue-tsc + vite, 0 type errors). The app now renders dark globally (cards/tables/menu dark). Confirm no build error.

- [ ] **Step 4: Commit**

```bash
git add web/src/styles/theme.css web/src/main.ts
git commit -m "feat(web): dark theme token layer + Element Plus dark integration"
```

---

## Task 2: 布局外壳 AppLayout.vue

**Files:** Modify `web/src/layouts/AppLayout.vue`.

**Use the `frontend-design` skill** for this task. READ the current `AppLayout.vue` first.

- [ ] **Step 1: Restyle with tokens** — replace all hard-coded hex in the `<style scoped>` with the `--aa-*` tokens. Target:
  - Sidebar: `background: var(--aa-surface)`; brand area with the accent (`--aa-accent`) logo mark + "AlphaAgent" wordmark; section group headers in `--aa-text-muted` uppercase small; `el-menu-item` active state = left 3px `--aa-accent` bar + `--aa-text` + subtle `--aa-surface-2` bg; hover transition 150ms.
  - Topbar: `background: var(--aa-surface)`, bottom border `--aa-border`; page title (`--aa-text`, 16px/600) + a muted subtitle line (the route's section, `--aa-text-muted`); keep the API 文档 link (style as a muted `el-link`).
  - Content: `background: var(--aa-bg)`, padding `var(--aa-5)`.
  - Add smooth `transition` on interactive elements; no pure-black, use the token surfaces.

Keep the template structure (el-container/el-aside/el-menu/router-view) intact — this is a styling pass. The menu must keep `router` mode + `:default-active="route.path"`.

- [ ] **Step 2: Build gate**

Run: `cd web && npm run build` → passes.

- [ ] **Step 3: Commit**

```bash
git add web/src/layouts/AppLayout.vue
git commit -m "feat(web): polished dark layout shell"
```

---

## Task 3: echarts 暗色主题

**Files:** Create `web/src/styles/echarts-dark.ts`; Modify `web/src/components/chart/{KLineChart,EquityChart,RankingBar}.vue`.

READ the three chart components first to see how they call `echarts.init(...)`.

- [ ] **Step 1: Create `web/src/styles/echarts-dark.ts`**

```typescript
import * as echarts from 'echarts'

// A-share convention: 涨=红 (--aa-pos), 跌=绿 (--aa-neg).
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
  // candlestick + line + bar default colors
  candlestick: {
    itemStyle: { color: '#f5455c', color0: '#27c08a', borderColor: '#f5455c', borderColor0: '#27c08a' },
  },
  color: ['#f0b429', '#5aa9e6', '#27c08a', '#f5455c', '#b48ead'],
})
```

- [ ] **Step 2: Apply the theme** — in each chart component, change the `echarts.init(el)` call to `echarts.init(el, AA_DARK)` and `import { AA_DARK } from '@/styles/echarts-dark'`. If a component hard-codes candle up/down colors in its option, point them at red-up/green-down (`#f5455c`/`#27c08a`) so they match. Replace any fixed white background. K-line container fixed `480px` height → keep but ensure it reads the dark theme (transparent bg lets the card surface show through).

- [ ] **Step 3: Build gate**

Run: `cd web && npm run build` → passes. (Charts now render on dark with red-up/green-down.)

- [ ] **Step 4: Commit**

```bash
git add web/src/styles/echarts-dark.ts web/src/components/chart/
git commit -m "feat(web): dark echarts theme (red-up/green-down) for all charts"
```

---

## Task 4: 公司分析页精修(不含 SP2 报告查看器)

**Files:** Modify `web/src/pages/analysis/company/Index.vue`; (optional) Create `web/src/components/common/StatCard.vue`.

**Use the `frontend-design` skill.** READ the current company page first.

- [ ] **Step 1: Restyle the page** — replace inline `style="..."` with classes + `--aa-*` tokens:
  - Header card: name (large, `--aa-text`) + symbol (muted) + industry/listed (muted subline); KPI block (总市值/流通市值/PE) as a clean stat row (consider a small `StatCard` with label muted + value `aa-num` tabular). Return tags: 红涨绿跌 via `--aa-pos`/`--aa-neg` (positive → red, negative → green), readable contrast on dark.
  - Search box visually connected to results (consistent card surface, not an isolated narrow card).
  - K-line card + financials table: dark surfaces, `--aa-border`, financial numbers `aa-num` right-aligned; table header subtle.
  - **AI 研判区**: keep the CURRENT card structure (rating tag + confidence + reasons/risks + disclaimer) but **theme it** with tokens/classes (remove inline styles). Add an `el-skeleton` shown while `agentLoading`. Add a comment marking this block as the SP2 report-viewer insertion point. DO NOT build the full report viewer / citation anchors here — that is SP2.
  - All cards: consistent header style (a left 2px `--aa-accent` accent or icon), `--aa-radius`, `--aa-shadow`.

- [ ] **Step 2: Build gate**

Run: `cd web && npm run build` → passes.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/analysis/company/Index.vue web/src/components/common/ 2>/dev/null; git add web/src/pages/analysis/company/Index.vue
git commit -m "feat(web): polish company analysis page (dark, tokens, stat cards)"
```

---

## Task 5: 其余页面 token 轻扫

**Files:** Modify `web/src/pages/{strategies,screener,analysis/industry,analysis/market,live}/Index.vue`.

**Use the `frontend-design` skill** judiciously (light touch; don't over-redesign).

- [ ] **Step 1: Sweep** — for each page, replace raw hex with `--aa-*` tokens and ensure dark readability:
  - `strategies`: table on dark surface; param tags styled.
  - `screener`: replace the raw `JSON.stringify(...)` detail dump with a small structured rendering (key/value rows or tags) on dark.
  - `industry`: selected-row highlight uses `--aa-surface-2`/accent instead of `#fef3c7`; ranking chart already themed by Task 3.
  - `market`: index cards + breadth bar use tokens (红涨绿跌); big northbound number `aa-num`.
  - `live`: dark `el-empty`.

- [ ] **Step 2: Build gate + full visual sanity**

Run: `cd web && npm run build` → passes.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages
git commit -m "feat(web): token sweep + dark polish across remaining pages"
```

---

## Self-Review

- **Spec coverage:** §3 tokens+EP dark → T1; §4 layout → T2; §5 echarts → T3; §6 company page (themed, hero deferred) → T4; §7 other pages → T5; §8 empty/loading → T4 (AI skeleton) + T5 (live empty); §10 acceptance → each task's build gate + final visual.
- **No real placeholders in deterministic parts:** T1 (theme.css) and T3 (echarts-dark.ts) have complete code. T2/T4/T5 are aesthetic component work — they give concrete token/structural direction + require the `frontend-design` skill; the precise polished CSS is produced during implementation (frontend styling has no unit-test analog; the gate is `npm run build` + user visual review).
- **Token consistency:** `--aa-bg/--aa-surface/--aa-surface-2/--aa-border/--aa-border-strong/--aa-text/--aa-text-muted/--aa-accent/--aa-pos/--aa-neg/--aa-radius/--aa-shadow/--aa-1..6` used consistently; EP override maps danger→pos(red), success→neg(green); echarts theme uses the same hex values (kept literal in the JS theme since CSS vars aren't readable inside the echarts option object).
- **Note:** the echarts theme hard-codes the hex (can't read CSS vars); keep it in sync with theme.css if the palette changes (documented in echarts-dark.ts comment).
