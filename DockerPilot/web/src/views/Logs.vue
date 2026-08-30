<template>
  <div>
    <a-card title="执行日志">
      <template #extra>
        <a-space>
          <a-input-search v-model:value="searchText" placeholder="搜索项目名称" style="width: 200px" allowClear />
          <a-select v-model:value="filterStatus" style="width: 120px" allowClear placeholder="状态筛选">
            <a-select-option value="success">成功</a-select-option>
            <a-select-option value="failed">失败</a-select-option>
            <a-select-option value="running">运行中</a-select-option>
          </a-select>
          <a-button @click="loadData" :loading="refreshing"><reload-outlined /></a-button>
        </a-space>
      </template>

      <!-- Stats -->
      <a-row :gutter="16" style="margin-bottom: 16px;">
        <a-col :span="6">
          <a-statistic title="总执行次数" :value="stats.total" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="成功" :value="stats.success" :value-style="{ color: '#52c41a' }" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="失败" :value="stats.failed" :value-style="{ color: '#ff4d4f' }" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="运行中" :value="stats.running" :value-style="{ color: '#faad14' }" />
        </a-col>
      </a-row>

      <a-skeleton :loading="loading" :paragraph="{ rows: 6 }" active v-if="loading" />

      <a-table v-else :dataSource="filteredLogs" :columns="columns" rowKey="id" :pagination="pagination" @change="handleTableChange" :size="'middle'" :scroll="{ x: 880 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span style="font-weight: 500;">{{ record.project_name || record.batch_name || '-' }}</span>
            <a-tag v-if="record.project_id" color="blue" size="small" style="margin-left: 4px;">项目</a-tag>
            <a-tag v-if="record.batch_group_id" color="purple" size="small" style="margin-left: 4px;">组合</a-tag>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusLabel(record.status) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'steps'">
            <a-space :size="4">
              <a-tag v-for="step in (record.steps || []).slice(0, 3)" :key="step.id" :color="getStepColor(step.status)" size="small">
                {{ getStepLabel(step.step_type) }}
              </a-tag>
              <a-tag v-if="(record.steps || []).length > 3" size="small">+{{ record.steps.length - 3 }}</a-tag>
            </a-space>
          </template>
          <template v-if="column.key === 'action'">
            <a-button type="link" size="small" @click="showDetail(record)">详情</a-button>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Detail Modal -->
    <a-modal v-model:open="detailModalVisible" title="执行详情" :footer="null" width="700px">
      <a-descriptions :column="2" bordered size="small" style="margin-bottom: 16px;">
        <a-descriptions-item label="ID">{{ detailData.id }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="getStatusColor(detailData.status)">{{ getStatusLabel(detailData.status) }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="项目">{{ detailData.project_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="组合">{{ detailData.batch_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="方案">{{ detailData.profile_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ formatTime(detailData.started_at) }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ formatTime(detailData.finished_at) || '-' }}</a-descriptions-item>
      </a-descriptions>

      <a-divider>执行步骤</a-divider>
      <a-timeline>
        <a-timeline-item v-for="step in (detailData.steps || [])" :key="step.id" :color="getStepColor(step.status)">
          <div style="display: flex; align-items: center; gap: 8px;">
            <a-tag :color="getStepColor(step.status)" size="small">
              {{ step.status === 'success' ? '✅' : step.status === 'failed' ? '❌' : '⏳' }}
            </a-tag>
            <span style="font-weight: bold;">{{ getStepLabel(step.step_type) }}</span>
          </div>
          <div v-if="step.output" style="margin-top: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px; font-size: 12px; text-align: left; white-space: pre-wrap; word-break: break-all; max-height: 150px; overflow-y: auto;">
            {{ step.output }}
          </div>
        </a-timeline-item>
      </a-timeline>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import axios from 'axios'

const logs = ref([])
const loading = ref(true)
const refreshing = ref(false)
const searchText = ref('')
const filterStatus = ref(null)
const stats = ref({ total: 0, success: 0, failed: 0, running: 0 })
const detailModalVisible = ref(false)
const detailData = ref({})
const sortInfo = ref({ field: 'started_at', order: 'descend' })
const pagination = ref({ current: 1, pageSize: 20, total: 0, showSizeChanger: true, showTotal: (total) => '共 ' + total + ' 条记录' })

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70, sorter: true, align: 'center' },
  { title: '名称', key: 'name', width: 200, sorter: true, ellipsis: true },
  { title: '状态', key: 'status', width: 100, sorter: true, align: 'center' },
  { title: '步骤', key: 'steps', width: 250 },
  { title: '开始时间', dataIndex: 'started_at', key: 'started_at', width: 180, sorter: true, ellipsis: true },
  { title: '操作', key: 'action', width: 80, fixed: 'right' },
]

const getStatusColor = (status) => {
  const colors = { success: 'success', failed: 'error', running: 'processing', pending: 'default' }
  return colors[status] || 'default'
}

const getStatusLabel = (status) => {
  const labels = { success: '成功', failed: '失败', running: '运行中', pending: '等待中' }
  return labels[status] || status
}

const getStepColor = (status) => {
  const colors = { success: 'green', failed: 'red', running: 'blue', pending: 'default' }
  return colors[status] || 'default'
}

const getStepLabel = (type) => {
  const labels = { image_pull: 'Pull', image_load: 'Load', project_run: 'Run' }
  return labels[type] || type
}

const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
}

const filteredLogs = computed(() => {
  let list = [...logs.value]
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(l =>
      (l.project_name || '').toLowerCase().includes(q) ||
      (l.batch_name || '').toLowerCase().includes(q)
    )
  }
  if (filterStatus.value) {
    list = list.filter(l => l.status === filterStatus.value)
  }
  const { field, order } = sortInfo.value
  list.sort((a, b) => {
    let aVal = a[field] || ''
    let bVal = b[field] || ''
    if (field === 'id') { aVal = Number(aVal); bVal = Number(bVal) }
    const cmp = aVal > bVal ? 1 : aVal < bVal ? -1 : 0
    return order === 'ascend' ? cmp : -cmp
  })
  pagination.value.total = list.length
  return list
})

const handleTableChange = (pag, filters, sorter) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  if (sorter.field) { sortInfo.value.field = sorter.field; sortInfo.value.order = sorter.order }
}

const loadData = async () => {
  loading.value = true
  refreshing.value = true
  try {
    const [logsRes, statsRes] = await Promise.all([
      axios.get('/api/logs?limit=200'),
      axios.get('/api/logs/stats/summary'),
    ])
    logs.value = logsRes.data.data.logs || []
    stats.value = statsRes.data.data || {}
  } catch (e) {
    message.error('加载日志失败')
  }
  loading.value = false
  refreshing.value = false
}

const showDetail = (record) => {
  detailData.value = record
  detailModalVisible.value = true
}

onMounted(loadData)
</script>
