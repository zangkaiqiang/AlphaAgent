<template>
  <div class="live-placeholder">
    <el-empty description="实盘 / 模拟盘监控 — 实时净值、持仓、订单流(开发中)" class="live-empty" />
  </div>
</template>

<style scoped>
.live-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  background: var(--aa-surface);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius);
}
.live-empty :deep(.el-empty__description p) {
  color: var(--aa-text-muted);
}
</style>
