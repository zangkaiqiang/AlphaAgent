# AlphaAgent Web

Vue 3 + Vite + TypeScript + Element Plus + ECharts.

## 开发

```bash
# 1) 启动后端(项目根目录)
pip install -e ".[api]"
alphaagent-api                                # 127.0.0.1:8000

# 2) 启动前端(在 web/ 目录)
npm install
npm run dev                                   # http://localhost:5173
```

Vite 已配置 `/api` 和 `/ws` 代理到 `http://127.0.0.1:8000`,无需手动跨域。

## 目录约定

```
src/
  layouts/AppLayout.vue       主壳:左侧菜单 + 内容区(菜单自动由 router 生成)
  router/                     路由 = 模块清单,每条 route.meta 决定菜单显示
  pages/<module>/             一级模块页面(backtest, strategies, screener, analysis/*, live)
  components/
    common/                   跨模块复用(后续:SymbolPicker、DateRange 等)
    chart/                    图表组件(EquityChart 已有,后续:KLineChart、Heatmap)
    *.vue                     业务组件
  api/                        每个模块一个文件,按需 import
  stores/                     Pinia(strategies 已缓存)
```

**加新模块的步骤**:
1. 在 `src/api/<module>.ts` 写 API 客户端
2. 在 `src/pages/<module>/Index.vue` 写页面
3. 在 `src/router/index.ts` 加一条 route(写 `meta.title/icon/section`),菜单自动更新

## 构建生产版本

```bash
npm run build      # 输出到 dist/
```
