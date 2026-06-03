<template>
  <div class="page">
    <el-card shadow="never" class="strategies-card">
      <template #header>策略库</template>
      <el-table :data="store.list" stripe class="strategies-table">
        <el-table-column prop="name" label="名称" width="220" />
        <el-table-column prop="class_name" label="实现类" width="240" />
        <el-table-column label="参数" min-width="280">
          <template #default="{ row }">
            <el-tag
              v-for="p in row.params"
              :key="p.name"
              type="info"
              effect="plain"
              size="small"
              class="param-tag"
            >
              {{ p.name }} ({{ p.type }}{{ p.default !== null ? `=${p.default}` : '' }})
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useStrategiesStore } from '@/stores/strategies'

const store = useStrategiesStore()
onMounted(() => store.load())
</script>

<style scoped>
.page {
  min-width: 0;
}
.strategies-card {
  background: var(--aa-surface);
  border: 1px solid var(--aa-border);
  border-radius: var(--aa-radius);
}
.strategies-table {
  background: var(--aa-surface);
}
.param-tag {
  margin-right: var(--aa-2);
  margin-bottom: 2px;
  background: var(--aa-surface-2);
  border-color: var(--aa-border-strong);
  color: var(--aa-text-muted);
  font-size: 12px;
}
</style>
