# 前端精修:深色专业盘面 设计(Effort A)

- 日期:2026-06-03
- 状态:待实现
- 关联:[[web-only-direction]]。这是两件事的 **Effort A**;**Effort B**(公司分析 agentic harness)随后单独走 spec→plan→实现。

## 1. 目标

把现在「裸 Element Plus 后台模板 + 满屏复制 hex + 内联样式」的前端,升级为**统一的深色专业盘面**(贴近行情终端/Bloomberg 观感),A股 **红涨绿跌**。范围:全局主题 token 层 + 布局外壳 + 公司分析页做旗舰;其余页自动继承暗色主题 + 轻扫。质量由 `frontend-design` 技能在落地阶段保证。

## 2. 现状(探查结论)

无设计 token、无全局样式、无主题覆盖;颜色裸 hex 复制于 10+ 文件;公司页 AI 卡片大量内联 `style=`;图表用默认白底;整体是 Element Plus demo 观感。最高杠杆:**先做全局 token + EP 暗色覆盖 + 布局外壳**,再精修公司页旗舰。

## 3. 设计 token 层

新增 `web/src/styles/theme.css`,定义深色盘面 CSS 变量(具体色值在落地时由 frontend-design 微调,以下为基线):

```
--bg:#0b0e14; --surface:#141a23; --surface-2:#1b2230; --border:#26303c;
--text:#e6edf3; --text-muted:#8b97a7;
--accent:#f0b429;            /* 品牌强调(沿用现有琥珀) */
--pos:#f5455c;               /* 涨=红(A股) */
--neg:#27c08a;               /* 跌=绿(A股) */
--radius:10px; --shadow:0 1px 0 rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.25);
--space-1..6 间距刻度; --font 数字等宽(行情数字用 tabular-nums)。
```

**启用 Element Plus 暗色**:`main.ts` 引入 `element-plus/theme-chalk/dark/css-vars.css`,给 `<html>` 加 `dark` 类;在 `theme.css` 用上面的 token **覆盖 EP 的 CSS 变量**(`--el-bg-color`、`--el-bg-color-overlay`、`--el-border-color`、`--el-text-color-*`、`--el-color-primary`、`--el-color-danger`(红)、`--el-color-success`(绿)等),使 EP 的卡片/表格/标签/按钮全局变深色专业风。涨跌色统一映射到 `--pos/--neg`。

## 4. 布局外壳 `AppLayout.vue`

- 侧栏:深底、品牌区(logo + AlphaAgent)、分组标题(研究/分析/交易)、选中态左强调条 + accent 色、hover 过渡。
- 顶栏:页面标题 + 副标题/面包屑;右侧保留 API 文档链接。
- 内容区:`--bg` 背景,统一 padding 与最大宽度。
- 用 class + token 替换内联 hex。

## 5. 图表深色化

新增 `web/src/styles/echarts-dark.ts`:一个 echarts 主题对象(深底、网格线 `--border`、坐标轴/文字 `--text-muted`、蜡烛 涨红跌绿),通过 `echarts.registerTheme('aa-dark', ...)` 注册;`KLineChart`/`EquityChart`/`RankingBar` 初始化时用该主题(`echarts.init(el, 'aa-dark')`)。容器改响应式高度(替换 K线固定 480px 内联)。

## 6. 公司分析页 `pages/analysis/company/Index.vue`

按新 token 精修(移除内联 `style=`,用 class):
- 头部:name/symbol/industry + KPI(总市值/流通市值/PE)统一 stat 样式;多窗口收益标签红涨绿跌。
- K线卡 + 财务表:按新 token 精修;财务表数字等宽对齐。
- 搜索框与结果视觉上连为一体。
- **AI 研判区**:SP1 仅做**深色化主题适配**(现有评级卡套用新风格),并**为 SP2 预留**报告查看器的位置。**带引用锚点的分章节报告查看器是 SP2 的旗舰内容,不在 SP1 实现**。

可选新增 `web/src/components/common/StatCard.vue` 统一 KPI/指标卡。

可选新增 `web/src/components/common/StatCard.vue` 统一 KPI/指标卡。

## 7. 其余页面

自动继承 EP 暗色 + token,无需逐页重写。低成本轻扫:`strategies` 表、`screener` 详情(用结构化渲染替代 `JSON.stringify` dump)、`market`/`industry` 的裸 hex 换 token。`live` 保持空态(深色化)。

## 8. 错误/空/加载态

深色化的 `el-empty`;公司页 AI 卡片加 skeleton;全局 ElMessage 在暗色下可读。

## 9. 文件清单

- 新增:`web/src/styles/theme.css`、`web/src/styles/echarts-dark.ts`、(可选)`web/src/components/common/StatCard.vue`。
- 修改:`web/src/main.ts`(引入 EP 暗色 css-vars + theme.css + `html.dark`)、`AppLayout.vue`、`pages/analysis/company/Index.vue`、`components/chart/*`(应用暗色主题)、各页裸 hex → token(布局+公司页必做,其余靠 EP 暗色兜底 + 轻扫)。

## 10. 验收

1. `cd web && npm run build`(vue-tsc + vite)通过,零类型错误。
2. 全局深色一致:侧栏/顶栏/卡片/表格/标签/图表均为深色盘面风,无残留白底卡片或裸 demo 观感。
3. 公司分析页 AI 区为醒目 hero(评级徽章 + 置信度 + 看多/风险双栏 + skeleton),无内联 `style=`。
4. A股 红涨绿跌 一致(收益标签、蜡烛、涨跌数字)。
5. 用户目视确认(前端无单测;质量靠 frontend-design + 视觉验收)。

## 11. 非目标 / 后续

- 不引入 Tailwind/UnoCSS(保持 Element Plus + token 层,YAGNI)。
- 不改后端/接口。
- Effort B(公司分析 agentic 工具循环)单独 spec;本次仅在公司页 AI 区**结构上预留**其展示位。
