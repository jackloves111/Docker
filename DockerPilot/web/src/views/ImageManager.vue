<template>
  <div>
    <!-- Pull Image -->
    <a-card title="拉取镜像" style="margin-bottom: 24px">
      <a-form layout="inline">
        <a-form-item label="镜像源">
          <a-select
            v-model:value="pullForm.registry_id"
            style="width: 240px"
            placeholder="选择镜像源"
            allowClear
          >
            <a-select-option :value="null">Docker Hub (默认)</a-select-option>
            <a-select-option v-for="r in registries" :key="r.id" :value="r.id">
              {{ r.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="镜像名">
          <a-input
            v-model:value="pullForm.image_name"
            placeholder="nginx:latest"
            style="width: 280px"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="handlePull" :loading="pulling">
            拉取
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- Load Image -->
    <a-card title="加载镜像" style="margin-bottom: 24px">
      <a-tabs v-model:activeKey="loadTab">
        <a-tab-pane key="url" tab="从URL加载">
          <a-form layout="inline">
            <a-form-item label="下载地址">
              <a-input
                v-model:value="loadForm.url"
                placeholder="https://example.com/image.tar"
                style="width: 480px"
              />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="handleLoadUrl" :loading="loadingUrl">
                下载并加载
              </a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
        <a-tab-pane key="upload" tab="上传本地文件">
          <a-upload
            :before-upload="handleBeforeUpload"
            :show-upload-list="false"
            accept=".tar,.tar.gz,.tgz"
          >
            <a-button type="primary" :loading="loadingUpload">
              <upload-outlined />
              选择tar文件
            </a-button>
          </a-upload>
          <div v-if="uploadFileName" style="margin-top: 8px">
            已选择: {{ uploadFileName }}
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- Auto-replace toggle -->
    <a-card style="margin-bottom: 24px; background: #f0f5ff; border: 1px solid #d6e4ff;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <a-switch v-model:checked="autoReplace" />
        <div>
          <span style="font-weight: 500;">拉取/导入后自动更新容器</span>
          <span style="color: #666; margin-left: 8px;">开启后，如果导入的镜像是某些容器正在使用的旧版本，自动重建这些容器</span>
        </div>
      </div>
    </a-card>

    <!-- Task Progress -->
    <a-card v-if="currentTask" title="任务进度" style="margin-bottom: 24px">
      <a-space direction="vertical" style="width: 100%">
        <div>
          <span>任务类型: </span>
          <a-tag :color="getTaskTypeColor(currentTask.type)">
            {{ getTaskTypeLabel(currentTask.type) }}
          </a-tag>
        </div>
        <div>
          <span>状态: </span>
          <a-tag :color="getTaskStatusColor(currentTask.status)">
            {{ getTaskStatusLabel(currentTask.status) }}
          </a-tag>
        </div>
        <div v-if="currentTask.name">
          <span>目标: </span>
          <span>{{ currentTask.name }}</span>
        </div>
        <a-progress
          :percent="currentTask.progress || 0"
          :status="getProgressStatus(currentTask.status)"
        />
        <div v-if="currentTask.message" style="color: #666">
          {{ currentTask.message }}
        </div>
        <div v-if="currentTask.detail" style="color: #999; font-size: 12px; margin-top: 2px;">
          {{ currentTask.detail }}
        </div>
        <div v-if="currentTask.output" style="margin-top: 8px">
          <a-collapse>
            <a-collapse-panel header="详细输出">
              <pre style="white-space: pre-wrap; margin: 0">{{ currentTask.output }}</pre>
            </a-collapse-panel>
          </a-collapse>
        </div>
      </a-space>
    </a-card>

    <!-- Image List -->
    <a-card title="本地镜像">
      <a-table
        :dataSource="images"
        :columns="columns"
        rowKey="id"
        :loading="loadingImages"
        @change="handleTableChange"
        :pagination="pagination"
        :scroll="{ x: 930 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'tags'">
            <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
              <template v-for="tag in record.tags" :key="`${record.id}-${tag}`">
                <a-tag
                  v-if="tag !== '<none>:<none>'"
                  :closable="record.tags.filter(t => t !== '<none>:<none>').length > 1"
                  @close="handleUntag(record.id, tag)"
                >
                  {{ tag }}
                </a-tag>
                <a-tag v-else color="default">
                  {{ tag }}
                </a-tag>
              </template>
              <a-button
                v-if="record.tags[0] !== '<none>:<none>'"
                type="link"
                size="small"
                @click="showTagModal(record)"
              >
                + 添加标签
              </a-button>
            </div>
          </template>
          <template v-if="column.key === 'in_use'">
            <a-tag :color="record.in_use ? 'red' : 'green'" size="small">
              {{ record.in_use ? '使用中' : '未使用' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'size'">
            {{ formatSize(record.size) }}
          </template>
          <template v-if="column.key === 'created'">
            {{ formatTime(record.created) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-popconfirm
              title="确定删除此镜像？"
              @confirm="handleDelete(record.id)"
            >
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Tag Modal -->
    <a-modal
      v-model:open="tagModalVisible"
      title="添加标签"
      @ok="handleTag"
      :confirmLoading="tagging"
    >
      <a-form layout="vertical">
        <a-form-item label="镜像ID">
          <a-input :value="tagModal.imageId" disabled />
        </a-form-item>
        <a-form-item label="仓库名" required>
          <a-input v-model:value="tagModal.repository" placeholder="myrepo/myapp" />
        </a-form-item>
        <a-form-item label="标签">
          <a-input v-model:value="tagModal.tag" placeholder="latest" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Result Modal -->
    <a-modal
      v-model:open="resultModalVisible"
      :title="resultModal.title"
      :footer="null"
      width="600px"
    >
      <div :style="{
        display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px',
        padding: '12px', borderRadius: '4px',
        background: resultModal.status === 'success' ? '#f6ffed' : '#fff2f0'
      }">
        <span style="font-size: 24px;">{{ resultModal.status === 'success' ? '✅' : '❌' }}</span>
        <span :style="{
          fontSize: '16px', fontWeight: 'bold',
          color: resultModal.status === 'success' ? '#52c41a' : '#ff4d4f'
        }">{{ resultModal.title }}</span>
      </div>
      <div v-if="resultModal.message" style="margin-bottom: 12px; color: #666;">
        {{ resultModal.message }}
      </div>
      <div v-if="resultModal.output" style="padding: 12px; background: #f5f5f5; border-radius: 4px; font-size: 12px; text-align: left; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto;">
        {{ resultModal.output }}
      </div>
      <div style="text-align: center; margin-top: 16px;">
        <a-button type="primary" @click="resultModalVisible = false">确定</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { UploadOutlined } from '@ant-design/icons-vue'
import { registriesAPI, imagesAPI, settingsAPI } from '../api'

const registries = ref([])
const images = ref([])
const pulling = ref(false)
const loadingUrl = ref(false)
const loadingUpload = ref(false)
const uploadStartTime = ref(0)
const loadingImages = ref(false)
const loadTab = ref('url')
const uploadFileName = ref('')
const currentTask = ref(null)
const taskPollTimer = ref(null)
const autoReplace = ref(false)  // Auto-replace containers after pull/load

// Persist auto_replace setting to database
watch(autoReplace, async (newVal) => {
  try {
    await settingsAPI.set('auto_replace', newVal.toString())
  } catch (e) {
    console.error('Failed to save setting:', e)
  }
})

const pullForm = ref({
  registry_id: null,
  image_name: '',
})

const loadForm = ref({
  url: '',
})

const resultModalVisible = ref(false)
const resultModal = ref({
  status: 'info',
  title: '',
  message: '',
  output: '',
})

// Tag modal
const tagModalVisible = ref(false)
const tagging = ref(false)
const tagModal = ref({
  imageId: '',
  repository: '',
  tag: 'latest',
})

// Sorting and pagination
const sortInfo = ref({
  field: 'created',
  order: 'descend',
})

const pagination = ref({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 个镜像`,
})

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 120, ellipsis: true },
  { title: '标签', key: 'tags', width: 350 },
  { title: '状态', key: 'in_use', width: 80, sorter: true, align: 'center' },
  { title: '大小', dataIndex: 'size', key: 'size', width: 120, sorter: true, align: 'right' },
  { title: '创建时间', dataIndex: 'created', key: 'created', width: 180, sorter: true, ellipsis: true },
  { title: '操作', key: 'action', width: 100, fixed: 'right' },
]

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

const formatSpeed = (bytesPerSec) => {
  if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s'
  if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s'
  if (bytesPerSec < 1024 * 1024 * 1024) return (bytesPerSec / 1024 / 1024).toFixed(1) + ' MB/s'
  return (bytesPerSec / 1024 / 1024 / 1024).toFixed(2) + ' GB/s'
}

const formatDuration = (seconds) => {
  if (seconds < 60) return Math.round(seconds) + '秒'
  if (seconds < 3600) return Math.floor(seconds / 60) + '分' + Math.round(seconds % 60) + '秒'
  return Math.floor(seconds / 3600) + '时' + Math.floor((seconds % 3600) / 60) + '分'
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

const getTaskTypeColor = (type) => {
  const colors = { image_pull: 'blue', image_load: 'cyan' }
  return colors[type] || 'default'
}

const getTaskTypeLabel = (type) => {
  const labels = { image_pull: 'Pull', image_load: 'Load' }
  return labels[type] || type
}

const getTaskStatusColor = (status) => {
  const colors = { pending: 'default', running: 'processing', success: 'success', failed: 'error' }
  return colors[status] || 'default'
}

const getTaskStatusLabel = (status) => {
  const labels = { pending: '等待中', running: '执行中', success: '成功', failed: '失败' }
  return labels[status] || status
}

const getProgressStatus = (status) => {
  const statuses = { success: 'success', failed: 'exception', running: 'active' }
  return statuses[status]
}

const sortImages = (data) => {
  const sorted = [...data]
  const { field, order } = sortInfo.value

  sorted.sort((a, b) => {
    let aVal = a[field]
    let bVal = b[field]

    // Handle size (number)
    if (field === 'size') {
      aVal = Number(aVal) || 0
      bVal = Number(bVal) || 0
    }

    // Handle created (string date)
    if (field === 'created') {
      aVal = new Date(aVal).getTime() || 0
      bVal = new Date(bVal).getTime() || 0
    }

    if (aVal < bVal) return order === 'ascend' ? -1 : 1
    if (aVal > bVal) return order === 'ascend' ? 1 : -1
    return 0
  })

  return sorted
}

const loadData = async () => {
  loadingImages.value = true
  try {
    const [regRes, imgRes, settingRes] = await Promise.all([
      registriesAPI.list(),
      imagesAPI.list(),
      settingsAPI.get('auto_replace'),
    ])
    registries.value = regRes.data.data
    const sortedImages = sortImages(imgRes.data.data)
    images.value = sortedImages
    pagination.value.total = sortedImages.length
    // Load auto_replace setting
    autoReplace.value = settingRes.data.data.value === 'true'
  } catch (e) {
    message.error('加载数据失败')
  }
  loadingImages.value = false
}

const handleTableChange = (pag, filters, sorter) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize

  if (sorter.field) {
    sortInfo.value.field = sorter.field
    sortInfo.value.order = sorter.order
    // Re-sort existing data
    images.value = sortImages(images.value)
  }
}

const startPollTask = (taskId) => {
  // Clear existing timer
  if (taskPollTimer.value) {
    clearInterval(taskPollTimer.value)
  }

  taskPollTimer.value = setInterval(async () => {
    try {
      const res = await imagesAPI.getTask(taskId)
      currentTask.value = res.data.data

      // Stop polling if task is done
      if (['success', 'failed'].includes(currentTask.value.status)) {
        clearInterval(taskPollTimer.value)
        taskPollTimer.value = null

        // Show result modal
        if (currentTask.value.status === 'success') {
          resultModal.value = {
            status: 'success',
            title: '操作成功',
            message: currentTask.value.message || '镜像操作完成',
            output: currentTask.value.output || '',
          }
          loadData() // Refresh image list
        } else {
          resultModal.value = {
            status: 'error',
            title: '操作失败',
            message: currentTask.value.error || currentTask.value.message || '未知错误',
            output: currentTask.value.output || '',
          }
        }
        resultModalVisible.value = true
        pulling.value = false
        loadingUrl.value = false
        loadingUpload.value = false
      }
    } catch (e) {
      console.error('Poll task failed:', e)
    }
  }, 1000)
}

const handlePull = async () => {
  if (!pullForm.value.image_name) {
    message.warning('请输入镜像名')
    return
  }
  pulling.value = true
  try {
    const res = await imagesAPI.pull({
      ...pullForm.value,
      auto_replace: autoReplace.value
    })
    const taskId = res.data.data.task_id
    currentTask.value = { status: 'pending', progress: 0, message: '任务已创建...' }
    startPollTask(taskId)
  } catch (e) {
    message.error(e.response?.data?.message || '拉取失败')
    pulling.value = false
  }
}

const handleLoadUrl = async () => {
  if (!loadForm.value.url) {
    message.warning('请输入下载地址')
    return
  }
  loadingUrl.value = true
  try {
    const res = await imagesAPI.load({
      url: loadForm.value.url,
      auto_replace: autoReplace.value
    })
    const taskId = res.data.data.task_id
    currentTask.value = { status: 'pending', progress: 0, message: '任务已创建...' }
    startPollTask(taskId)
  } catch (e) {
    message.error(e.response?.data?.message || '加载失败')
    loadingUrl.value = false
  }
}

const handleBeforeUpload = async (file) => {
  uploadFileName.value = file.name
  loadingUpload.value = true
  uploadStartTime.value = Date.now()

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('auto_replace', autoReplace.value ? 'true' : 'false')

    const res = await imagesAPI.loadUpload(formData, (progressEvent) => {
      const loaded = progressEvent.loaded
      const total = progressEvent.total || file.size
      const percent = Math.round((loaded * 100) / total)
      const elapsed = (Date.now() - uploadStartTime.value) / 1000
      const speed = elapsed > 0 ? loaded / elapsed : 0
      const speedStr = formatSpeed(speed)
      const remaining = speed > 0 ? (total - loaded) / speed : 0
      const remainStr = remaining > 0 ? formatDuration(remaining) : ''

      currentTask.value = {
        status: 'running',
        progress: percent,
        message: `📤 上传文件 ${percent}% — ${formatSize(loaded)} / ${formatSize(total)}`,
        detail: `速度: ${speedStr}${remainStr ? '  |  剩余: ' + remainStr : ''}`,
      }
    })

    const taskId = res.data.data.task_id
    currentTask.value = { status: 'pending', progress: 0, message: '文件已上传，正在加载到 Docker...' }
    startPollTask(taskId)
  } catch (e) {
    message.error(e.response?.data?.message || '上传失败')
    loadingUpload.value = false
  }

  return false // Prevent default upload
}

const handleDelete = async (id) => {
  try {
    await imagesAPI.delete(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

const showTagModal = (record) => {
  tagModal.value = {
    imageId: record.id,
    repository: '',
    tag: 'latest',
  }
  tagModalVisible.value = true
}

const handleTag = async () => {
  if (!tagModal.value.repository) {
    message.warning('请输入仓库名')
    return
  }
  tagging.value = true
  try {
    await imagesAPI.tag(tagModal.value.imageId, tagModal.value.repository, tagModal.value.tag)
    message.success('标签添加成功')
    tagModalVisible.value = false
    // 本地直接更新
    const img = images.value.find(i => i.id === tagModal.value.imageId)
    if (img) {
      const newTag = `${tagModal.value.repository}:${tagModal.value.tag}`
      if (img.tags.includes('<none>:<none>')) {
        img.tags = [newTag]
      } else if (!img.tags.includes(newTag)) {
        img.tags = [...img.tags, newTag]
      }
    }
  } catch (e) {
    message.error(e.response?.data?.message || '添加标签失败')
  }
  tagging.value = false
}

const handleUntag = async (imageId, tag) => {
  try {
    await imagesAPI.untag(imageId, tag)
    message.success('标签删除成功')
    // 本地直接更新，避免全量刷新导致渲染异常
    const img = images.value.find(i => i.id === imageId)
    if (img) {
      const remaining = img.tags.filter(t => t !== tag)
      img.tags = remaining.length > 0 ? remaining : ['<none>:<none>']
    }
  } catch (e) {
    message.error(e.response?.data?.message || '删除标签失败')
  }
}

onMounted(loadData)

onUnmounted(() => {
  if (taskPollTimer.value) {
    clearInterval(taskPollTimer.value)
  }
})
</script>
