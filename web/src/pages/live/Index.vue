<template>
  <div class="live-placeholder">
    <el-empty description="实盘 / 模拟盘监控开发中" class="live-empty" />
  </div>
</template>

<style scoped>
.live-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: min(520px, calc(100vh - 128px));
  background: var(--aa-surface);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius);
  box-shadow: var(--aa-shadow);
}
.live-empty :deep(.el-empty__description p) {
  color: var(--aa-text-muted);
}
</style>
