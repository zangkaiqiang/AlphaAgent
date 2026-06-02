<template>
  <el-table :data="rows" stripe size="small" max-height="320">
    <el-table-column prop="timestamp" label="时间" width="170" />
    <el-table-column prop="symbol" label="代码" width="100" />
    <el-table-column label="方向" width="80">
      <template #default="{ row }">
        <el-tag :type="row.side === 'BUY' ? 'danger' : 'success'" size="small">
          {{ row.side === 'BUY' ? '买入' : '卖出' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="quantity" label="数量" width="100" align="right" />
    <el-table-column label="成交价" width="100" align="right">
      <template #default="{ row }">{{ row.fill_price.toFixed(3) }}</template>
    </el-table-column>
    <el-table-column label="佣金" width="100" align="right">
      <template #default="{ row }">{{ row.commission.toFixed(2) }}</template>
    </el-table-column>
    <el-table-column label="印花税" width="100" align="right">
      <template #default="{ row }">{{ row.stamp_tax.toFixed(2) }}</template>
    </el-table-column>
    <el-table-column prop="strategy_id" label="策略" />
  </el-table>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FillDTO } from '@/api/types'
import dayjs from 'dayjs'

const props = defineProps<{ fills: FillDTO[] }>()

const rows = computed(() =>
  props.fills.map(f => ({
    ...f,
    timestamp: dayjs(f.timestamp).format('YYYY-MM-DD HH:mm'),
  })),
)
</script>
