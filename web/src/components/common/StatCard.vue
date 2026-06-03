<template>
  <div class="stat-card">
    <div class="stat-label aa-muted">{{ label }}</div>
    <div class="stat-value aa-num" :class="valueClass">{{ value }}</div>
    <div v-if="sub" class="stat-sub aa-muted">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string
  sub?: string
  /** 'pos' | 'neg' | '' — applies aa-pos / aa-neg color */
  valueClass?: string
}>()
</script>

<style scoped>
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--aa-3) var(--aa-4);
  background: var(--aa-surface-2);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius-sm);
  min-width: 120px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.025) inset;
}
.stat-label {
  font-size: 11px;
  letter-spacing: 0;
}
.stat-value {
  font-size: 17px;
  font-weight: 600;
  color: var(--aa-text);
  line-height: 1.2;
}
.stat-sub {
  font-size: 11px;
}
</style>
