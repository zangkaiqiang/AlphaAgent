<template>
  <el-card shadow="never">
    <template #header>策略库</template>
    <el-table :data="store.list" stripe>
      <el-table-column prop="name" label="名称" width="220" />
      <el-table-column prop="class_name" label="实现类" width="240" />
      <el-table-column label="参数">
        <template #default="{ row }">
          <el-tag
            v-for="p in row.params"
            :key="p.name"
            type="info"
            effect="plain"
            size="small"
            style="margin-right: 6px;"
          >
            {{ p.name }} ({{ p.type }}{{ p.default !== null ? `=${p.default}` : '' }})
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="说明" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useStrategiesStore } from '@/stores/strategies'

const store = useStrategiesStore()
onMounted(() => store.load())
</script>
