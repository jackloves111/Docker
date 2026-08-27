<template>
  <div>
    <a-card title="Docker 容器">
      <template #extra>
        <a-space>
          <a-input-search v-model:value="searchText" placeholder="搜索容器名称/镜像" style="width: 240px" allowClear />
          <a-button @click="loadData" :loading="refreshing"><reload-outlined /></a-button>
        </a-space>
      </template>
      <a-skeleton :loading="loading" :paragraph="{ rows: 8 }" active v-if="loading" />
      <a-table v-else :dataSource="filteredContainers" :columns="columns" rowKey="id" :pagination="pagination" @change="handleTableChange" :size="'middle'">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span style="font-weight: 500;">{{ record.name }}</span>
          </template>
          <template v-if="column.key === 'status'">
            <div style="display: flex; align-items: center; gap: 6px;">
              <span :style="{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', backgroundColor: getStateColor(record.state), boxShadow: record.state === 'running' ? '0 0 6px ' + getStateColor(record.state) : 'none' }"></span>
              <span>{{ record.state }}</span>
            </div>
          </template>
          <template v-if="column.key === 'created'">
            {{ formatTime(record.created) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space :size="4">
              <a-button type="link" size="small" @click="showLogs(record)">日志</a-button>
              <a-divider type="vertical" />
              <a-button type="link" size="small" @click="showRedeployModal(record)">重新部署</a-button>
              <a-divider type="vertical" />
              <a-button v-if="record.state === 'running'" type="link" size="small" @click="handleStop(record.id)">停止</a-button>
              <a-button v-if="record.state === 'exited'" type="link" size="small" @click="handleStart(record.id)">启动</a-button>
              <a-popconfirm title="确定删除此容器？" @confirm="handleRemove(record.id)">
                <a-button type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
    <a-modal v-model:open="logsModalVisible" :title="'容器日志 - ' + (logsContainer?.name || '')" :footer="null" width="800px">
      <a-spin :spinning="loadingLogs">
        <pre style="background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 4px; max-height: 500px; overflow-y: auto; font-size: 12px">{{ logs }}</pre>
      </a-spin>
    </a-modal>

    <!-- Redeploy Modal -->
    <a-modal v-model:open="redeployModalVisible" title="重新部署容器" @ok="handleRedeploy" :confirmLoading="redeploying" width="500px">
      <a-alert type="info" show-icon style="margin-bottom: 16px">
        <template #message>确认重新部署此容器？</template>
        <template #description>
          将使用本地镜像 <b>{{ redeployContainer?.image }}</b> 重新创建容器（不拉取远程镜像）。如果本地已有最新版本，容器将自动更新。
        </template>
      </a-alert>
      <a-descriptions :column="1" size="small" bordered>
        <a-descriptions-item label="容器名称">{{ redeployContainer?.name }}</a-descriptions-item>
        <a-descriptions-item label="当前镜像">{{ redeployContainer?.image }}</a-descriptions-item>
        <a-descriptions-item label="状态">{{ redeployContainer?.state }}</a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'
import { containersAPI } from '../api'

const containers = ref([])
const loading = ref(true)
const refreshing = ref(false)
const searchText = ref('')
const logsModalVisible = ref(false)
const loadingLogs = ref(false)
const logsContainer = ref(null)
const logs = ref('')
const sortInfo = ref({ field: 'name', order: 'ascend' })
const pagination = ref({ current: 1, pageSize: 20, total: 0, showSizeChanger: true, showTotal: (total) => '共 ' + total + ' 个容器' })

// Redeploy
const redeployModalVisible = ref(false)
const redeploying = ref(false)
const redeployContainer = ref(null)
const redeployImage = ref('')

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 100, sorter: true },
  { title: '名称', key: 'name', width: 200, sorter: true },
  { title: '镜像', dataIndex: 'image', key: 'image', width: 250, sorter: true },
  { title: '状态', key: 'status', width: 100, sorter: true },
  { title: '创建时间', dataIndex: 'created', key: 'created', width: 150, sorter: true },
  { title: '操作', key: 'action', width: 160 },
]

const getStateColor = (state) => {
  const colors = { running: '#52c41a', exited: '#ff4d4f', paused: '#faad14', created: '#1890ff', restarting: '#faad14' }
  return colors[state] || '#d9d9d9'
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  try {
    const d = new Date(timeStr)
    if (isNaN(d.getTime())) return timeStr
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch {
    return timeStr
  }
}

const filteredContainers = computed(() => {
  let list = [...containers.value]
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(c => c.name.toLowerCase().includes(q) || c.image.toLowerCase().includes(q))
  }
  const { field, order } = sortInfo.value
  list.sort((a, b) => { const cmp = (a[field] || '').localeCompare(b[field] || ''); return order === 'ascend' ? cmp : -cmp })
  pagination.value.total = list.length
  return list
})

const handleTableChange = (pag, filters, sorter) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  if (sorter.field) { sortInfo.value.field = sorter.field; sortInfo.value.order = sorter.order }
}

const loadData = async (silent = false) => {
  if (!silent) loading.value = true
  refreshing.value = true
  try {
    const res = await containersAPI.list()
    containers.value = res.data.data || []
  } catch (e) { message.error('加载失败') }
  loading.value = false
  refreshing.value = false
}

const showLogs = async (container) => {
  logsContainer.value = container; logs.value = ''; logsModalVisible.value = true; loadingLogs.value = true
  try { const r = await containersAPI.logs(container.id, 200); logs.value = r.data.data.logs || 'No logs' } catch (e) { logs.value = 'Failed' }
  loadingLogs.value = false
}

const handleStop = async (id) => { try { await containersAPI.stop(id); message.success('已停止'); loadData(true) } catch (e) { message.error('停止失败') } }
const handleStart = async (id) => { try { await containersAPI.start(id); message.success('已启动'); loadData(true) } catch (e) { message.error('启动失败') } }
const handleRemove = async (id) => { try { await containersAPI.remove(id); message.success('已删除'); loadData(true) } catch (e) { message.error('删除失败') } }

// Redeploy
const showRedeployModal = (container) => {
  redeployContainer.value = container
  redeployImage.value = container.image || ''
  redeployModalVisible.value = true
}

const handleRedeploy = async () => {
  redeploying.value = true
  try {
    // Portainer style: only pass containerId, image comes from Config.Image
    const res = await containersAPI.replace(
      redeployContainer.value.full_id || redeployContainer.value.id
    )
    const result = res.data.data.result || res.data.data
    if (result?.success) {
      message.success('重新部署成功')
    } else {
      message.error(result?.error || '重新部署失败')
    }
    redeployModalVisible.value = false
    loadData(true)
  } catch (e) {
    message.error(e.response?.data?.message || '重新部署失败')
  }
  redeploying.value = false
}

onMounted(() => loadData())
onActivated(() => loadData(true))
</script>
