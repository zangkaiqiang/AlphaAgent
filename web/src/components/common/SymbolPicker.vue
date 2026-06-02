<template>
  <el-input
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    @keyup.enter="emit('submit')"
    placeholder="6 位股票代码,如 600000"
    clearable
  >
    <template #prefix><el-icon><Search /></el-icon></template>
    <template #append>
      <el-button type="primary" :icon="Search" @click="emit('submit')">查询</el-button>
    </template>
  </el-input>
</template>

<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'submit'): void
}>()
</script>
