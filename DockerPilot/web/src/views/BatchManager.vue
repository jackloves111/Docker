<template>
  <div>
    <a-card title="批量组合">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          新建组合
        </a-button>
      </template>

      <a-table :dataSource="batches" :columns="columns" rowKey="id" :loading="loading" :pagination="false">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="cursor: pointer; user-select: none;" @click="toggleExpand(record.id)">
                {{ expandedRows.includes(record.id) ? '▼' : '▶' }}
              </span>
              <a-input
                v-if="editingNameId === record.id"
                v-model:value="editingNameValue"
                size="small"
                @pressEnter="saveName(record)"
                @blur="saveName(record)"
                style="width: 200px;"
              />
              <span v-else @dblclick="startEditName(record)" style="cursor: pointer;">
                {{ record.name }}
              </span>
            </div>
          </template>

          <template v-if="column.key === 'items'">
            <div v-if="expandedRows.includes(record.id)">
              <draggable
                :list="record.items"
                item-key="id"
                handle=".drag-handle"
                @end="(e) => handleDragEnd(record, e)"
                style="min-height: 40px;"
              >
                <template #item="{ element: item, index }">
                  <div class="item-row">
                    <span class="drag-handle" style="cursor: grab; margin-right: 8px;">≡</span>
                    <a-tag :color="getItemColor(item.item_type)" style="margin-right: 8px;">
                      {{ getItemLabel(item.item_type) }}
                    </a-tag>
                    <span style="flex: 1;">{{ getItemDisplayName(item) }}</span>
                    <a-tooltip v-if="item.auto_replace" title="已开启：更新后自动重建容器">
                      <a-tag color="green" size="small" style="margin-right: 8px; cursor: pointer;" @click="toggleItemAutoReplace(record, item)">🔄 自动更新</a-tag>
                    </a-tooltip>
                    <a-tooltip v-else title="点击开启自动更新">
                      <a-tag size="small" style="margin-right: 8px; cursor: pointer; color: #999;" @click="toggleItemAutoReplace(record, item)">手动更新</a-tag>
                    </a-tooltip>
                    <a-button type="link" danger size="small" @click="deleteItem(record, item.id)">
                      删除
                    </a-button>
                  </div>
                </template>
              </draggable>
              <a-button
                type="dashed"
                block
                size="small"
                @click="showAddItemModal(record)"
                style="margin-top: 8px;"
              >
                + 添加项
              </a-button>
            </div>
            <div v-else>
              <span v-for="(item, idx) in (record.items || []).slice(0, 3)" :key="item.id">
                <a-tag :color="getItemColor(item.item_type)" size="small">
                  {{ getItemLabel(item.item_type) }} {{ getItemDisplayName(item) }}
                  <template v-if="item.auto_replace">🔄</template>
                </a-tag>
              </span>
              <span v-if="(record.items || []).length > 3" style="color: #999; margin-left: 4px;">
                +{{ record.items.length - 3 }}项
              </span>
              <span v-if="(record.items || []).length === 0" style="color: #999;">暂无项</span>
            </div>
          </template>

          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="showExecuteModal(record)">
                执行
              </a-button>
              <a-popconfirm
                title="确定删除此组合？"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>

        <template #footer>
          <div class="add-row" @click="startAddBatch">
            <template v-if="isAdding">
              <a-input
                v-model:value="newBatchName"
                placeholder="输入组合名称"
                size="small"
                style="width: 200px; margin-right: 8px;"
                @pressEnter="confirmAddBatch"
                @blur="confirmAddBatch"
                ref="newBatchInput"
              />
              <a-button size="small" type="primary" @click="confirmAddBatch">确认</a-button>
              <a-button size="small" @click="cancelAddBatch">取消</a-button>
            </template>
            <template v-else>
              <span style="color: #999;">+ 点击新增组合</span>
            </template>
          </div>
        </template>
      </a-table>
    </a-card>

    <!-- 新建组合弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingBatch ? '编辑组合' : '新建组合'"
      @ok="handleSubmit"
      :confirmLoading="submitting"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="组合名称" required>
          <a-input v-model:value="form.name" placeholder="新设备部署套件" />
        </a-form-item>
        <a-form-item label="失败时继续执行">
          <a-switch v-model:checked="form.continue_on_error" />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="form.description" placeholder="组合描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 执行弹窗 -->
    <a-modal
      v-model:open="executeModalVisible"
      title="执行批量组合"
      @ok="handleExecute"
      :confirmLoading="executing"
      width="700px"
    >
      <VariableSelector
        :requiredVars="batchRequiredVars"
        @update:profileId="(val) => executeForm.profile_id = val"
        @update:overrides="(val) => executeOverrides = val"
        @update:valid="(val) => executeValid = val"
      />

      <a-divider>组合内容</a-divider>
      <a-list :dataSource="executingBatch?.items || []" size="small">
        <template #renderItem="{ item, index }">
          <a-list-item>
            <a-list-item-meta>
              <template #title>
                <a-tag :color="getItemColor(item.item_type)">
                  {{ getItemLabel(item.item_type) }}
                </a-tag>
                <span style="margin-left: 8px">{{ index + 1 }}. {{ getItemDisplayName(item) }}</span>
                <a-tooltip v-if="item.auto_replace" title="自动更新已开启">
                  <a-tag color="green" size="small" style="margin-left: 8px;">🔄 自动更新</a-tag>
                </a-tooltip>
              </template>
            </a-list-item-meta>
          </a-list-item>
        </template>
      </a-list>
    </a-modal>

    <!-- 添加项弹窗 -->
    <a-modal
      v-model:open="addItemModalVisible"
      title="添加组合项"
      @ok="handleAddItem"
      :confirmLoading="addingItem"
    >
      <a-form :model="itemForm" layout="vertical">
        <a-form-item label="类型" required>
          <a-select v-model:value="itemForm.item_type">
            <a-select-option value="image_pull">Pull 镜像</a-select-option>
            <a-select-option value="image_load">Load 镜像</a-select-option>
            <a-select-option value="project_run">运行项目</a-select-option>
          </a-select>
        </a-form-item>

        <template v-if="itemForm.item_type === 'image_pull'">
          <a-form-item label="镜像名" required>
            <a-input v-model:value="itemForm.config.image_name" placeholder="nginx:latest" />
          </a-form-item>
          <a-form-item label="镜像源">
            <a-select v-model:value="itemForm.config.registry_id" placeholder="选择镜像源" allowClear>
              <a-select-option v-for="r in registries" :key="r.id" :value="r.id">
                {{ r.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="拉取后自动更新容器">
            <a-switch v-model:checked="itemForm.auto_replace" />
            <span style="margin-left: 8px; color: #666;">如有容器使用旧版本镜像，自动重建</span>
          </a-form-item>
        </template>

        <template v-if="itemForm.item_type === 'image_load'">
          <a-form-item label="下载地址" required>
            <a-input v-model:value="itemForm.config.url" placeholder="https://example.com/image.tar" />
          </a-form-item>
          <a-form-item label="加载后自动更新容器">
            <a-switch v-model:checked="itemForm.auto_replace" />
            <span style="margin-left: 8px; color: #666;">如有容器使用旧版本镜像，自动重建</span>
          </a-form-item>
        </template>

        <template v-if="itemForm.item_type === 'project_run'">
          <a-form-item label="选择项目" required>
            <a-select v-model:value="itemForm.item_id" placeholder="选择项目">
              <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
                {{ p.name }} ({{ p.type }})
              </a-select-option>
            </a-select>
          </a-form-item>
        </template>
      </a-form>
    </a-modal>

    <!-- 执行结果弹窗 -->
    <a-modal
      v-model:open="resultModalVisible"
      title="执行结果"
      :footer="null"
      width="700px"
    >
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 12px; border-radius: 4px;" :style="{ background: resultData.success ? '#f6ffed' : '#fff2f0' }">
        <span style="font-size: 24px;">{{ resultData.success ? '✅' : '❌' }}</span>
        <span style="font-size: 16px; font-weight: bold;" :style="{ color: resultData.success ? '#52c41a' : '#ff4d4f' }">
          {{ resultData.success ? '执行成功' : '执行失败' }}
        </span>
      </div>
      <a-divider style="margin: 12px 0;">执行步骤详情</a-divider>
      <a-timeline>
        <a-timeline-item
          v-for="step in resultData.steps"
          :key="step.id"
          :color="step.status === 'success' ? 'green' : step.status === 'failed' ? 'red' : 'gray'"
        >
          <div style="display: flex; align-items: center; gap: 8px;">
            <a-tag :color="step.status === 'success' ? 'success' : step.status === 'failed' ? 'error' : 'default'" size="small">
              {{ step.status === 'success' ? '✅' : step.status === 'failed' ? '❌' : '⏳' }}
            </a-tag>
            <span style="font-weight: bold;">{{ getStepTypeLabel(step.type) }}</span>
            <span style="color: #999;">{{ getStepDescription(step) }}</span>
          </div>
          <div v-if="step.output" style="margin-top: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px; font-size: 12px; text-align: left; white-space: pre-wrap; word-break: break-all;">
            {{ step.output }}
          </div>
        </a-timeline-item>
      </a-timeline>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import draggable from 'vuedraggable'
import { batchesAPI, registriesAPI, projectsAPI } from '../api'
import VariableSelector from '../components/VariableSelector.vue'

const batches = ref([])
const registries = ref([])
const projects = ref([])
const loading = ref(false)
const expandedRows = ref([])

// Name editing
const editingNameId = ref(null)
const editingNameValue = ref('')

// Add batch
const isAdding = ref(false)
const newBatchName = ref('')
const newBatchInput = ref(null)

// Execute modal
const executeModalVisible = ref(false)
const executing = ref(false)
const executingBatch = ref(null)
const executeForm = ref({ profile_id: null })
const executeOverrides = ref({})
const executeValid = ref(true)
const batchRequiredVars = ref([])

// Result modal
const resultModalVisible = ref(false)
const resultData = ref({
  success: false,
  steps: []
})

// Add item modal
const addItemModalVisible = ref(false)
const addingItem = ref(false)
const addingToBatch = ref(null)
const itemForm = ref({
  item_type: 'image_pull',
  item_id: null,
  config: {},
  auto_replace: false,
})

const columns = [
  { title: 'ID', dataIndex: 'id', width: 60 },
  { title: '名称', key: 'name', width: 250 },
  { title: '包含项', key: 'items' },
  { title: '操作', key: 'action', width: 150 },
]

const getItemColor = (type) => {
  const colors = { image_pull: 'blue', image_load: 'cyan', project_run: 'green' }
  return colors[type] || 'default'
}

const getItemLabel = (type) => {
  const labels = { image_pull: 'Pull', image_load: 'Load', project_run: 'Run' }
  return labels[type] || type
}

const getStepTypeLabel = (type) => {
  const labels = { image_pull: '拉取镜像', image_load: '加载镜像', project_run: '运行项目' }
  return labels[type] || type
}

const getStepDescription = (step) => {
  const config = step.config || {}
  if (step.type === 'image_pull') return config.image_name || ''
  if (step.type === 'image_load') {
    const url = config.url || ''
    return url.length > 30 ? url.substring(0, 27) + '...' : url
  }
  if (step.type === 'project_run') {
    const project = projects.value.find(p => p.id === step.config?.project_id)
    return project ? project.name : `#${step.config?.project_id}`
  }
  return ''
}

const getItemDisplayName = (item) => {
  const config = typeof item.item_config === 'string' ? JSON.parse(item.item_config) : item.item_config
  if (item.item_type === 'image_pull') return config.image_name || '-'
  if (item.item_type === 'image_load') {
    const url = config.url || ''
    return url.length > 40 ? url.substring(0, 37) + '...' : url
  }
  if (item.item_type === 'project_run') {
    const project = projects.value.find(p => p.id === item.item_id)
    return project ? project.name : `#${item.item_id}`
  }
  return '-'
}

// Extract variables from batch items (project_run type)
const extractBatchVariables = (batch) => {
  const vars = new Set()
  const regex = /\$\{(\w+)\}|\$(\w+)/g
  for (const item of (batch.items || [])) {
    if (item.item_type === 'project_run') {
      const project = projects.value.find(p => p.id === item.item_id)
      if (project) {
        const content = (project.command || '') + ' ' + (project.compose_content || '')
        let match
        while ((match = regex.exec(content)) !== null) {
          vars.add(match[1] || match[2])
        }
      }
    }
  }
  return [...vars]
}

const loadData = async () => {
  loading.value = true
  try {
    const [batchRes, regRes, projRes] = await Promise.all([
      batchesAPI.list(),
      registriesAPI.list(),
      projectsAPI.list(),
    ])
    batches.value = batchRes.data.data
    registries.value = regRes.data.data
    projects.value = projRes.data.data
  } catch (e) {
    message.error('加载数据失败')
  }
  loading.value = false
}

const showCreateModal = () => {
  editingBatch.value = null
  form.value = {
    name: '',
    continue_on_error: false,
    description: '',
  }
  modalVisible.value = true
}

const editBatch = (batch) => {
  editingBatch.value = batch
  form.value = {
    name: batch.name,
    continue_on_error: batch.continue_on_error,
    description: batch.description || '',
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name) {
    message.warning('请输入组合名称')
    return
  }
  submitting.value = true
  try {
    if (editingBatch.value) {
      await batchesAPI.update(editingBatch.value.id, form.value)
      message.success('更新成功')
    } else {
      await batchesAPI.create(form.value)
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (e) {
    message.error(e.response?.data?.message || '操作失败')
  }
  submitting.value = false
}

const handleDelete = async (id) => {
  try {
    await batchesAPI.delete(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

// Expand/collapse row
const toggleExpand = (id) => {
  const idx = expandedRows.value.indexOf(id)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value.push(id)
  }
}

// Edit name
const startEditName = (record) => {
  editingNameId.value = record.id
  editingNameValue.value = record.name
}

const saveName = async (record) => {
  if (editingNameValue.value && editingNameValue.value !== record.name) {
    try {
      await batchesAPI.update(record.id, { name: editingNameValue.value })
      record.name = editingNameValue.value
    } catch (e) {
      message.error('更新名称失败')
    }
  }
  editingNameId.value = null
}

// Add batch
const startAddBatch = () => {
  if (isAdding.value) return
  isAdding.value = true
  newBatchName.value = ''
  nextTick(() => {
    newBatchInput.value?.focus()
  })
}

const confirmAddBatch = async () => {
  if (!newBatchName.value) {
    cancelAddBatch()
    return
  }
  try {
    const res = await batchesAPI.create({ name: newBatchName.value })
    message.success('创建成功')
    isAdding.value = false
    loadData()
  } catch (e) {
    message.error('创建失败')
  }
}

const cancelAddBatch = () => {
  isAdding.value = false
  newBatchName.value = ''
}

// Drag end handler
const handleDragEnd = async (record, event) => {
  const updates = record.items.map((item, idx) => ({
    id: item.id,
    sort_order: idx
  }))
  try {
    await batchesAPI.reorderItems(record.id, { item_orders: updates })
  } catch (e) {
    message.error('排序失败')
  }
}

// Add item
const showAddItemModal = (batch) => {
  addingToBatch.value = batch
  itemForm.value = {
    item_type: 'image_pull',
    item_id: null,
    config: {},
    auto_replace: false,
  }
  addItemModalVisible.value = true
}

const handleAddItem = async () => {
  addingItem.value = true
  try {
    const data = {
      item_type: itemForm.value.item_type,
      item_id: itemForm.value.item_id,
      item_config: itemForm.value.config,
      auto_replace: itemForm.value.auto_replace,
      sort_order: (addingToBatch.value.items || []).length,
    }
    await batchesAPI.addItem(addingToBatch.value.id, data)
    message.success('添加成功')
    addItemModalVisible.value = false
    loadData()
  } catch (e) {
    message.error(e.response?.data?.message || '添加失败')
  }
  addingItem.value = false
}

// Delete item
const deleteItem = async (batch, itemId) => {
  try {
    await batchesAPI.deleteItem(batch.id, itemId)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

// Toggle item auto_replace
const toggleItemAutoReplace = async (batch, item) => {
  const newVal = item.auto_replace ? 0 : 1
  try {
    await batchesAPI.updateItem(batch.id, item.id, { auto_replace: newVal })
    item.auto_replace = newVal
    message.success(newVal ? '已开启自动更新' : '已关闭自动更新')
  } catch (e) {
    message.error('切换失败')
  }
}

// Execute
const showExecuteModal = (batch) => {
  executingBatch.value = batch
  executeForm.value.profile_id = null
  executeOverrides.value = {}
  batchRequiredVars.value = extractBatchVariables(batch)
  executeModalVisible.value = true
}

const handleExecute = async () => {
  executing.value = true
  try {
    const res = await batchesAPI.execute(executingBatch.value.id, {
      profile_id: executeForm.value.profile_id,
      overrides: Object.keys(executeOverrides.value).length > 0 ? executeOverrides.value : undefined,
    })
    resultData.value = {
      success: res.data.data.success,
      steps: res.data.data.steps || []
    }
    resultModalVisible.value = true
    executeModalVisible.value = false
  } catch (e) {
    message.error(e.response?.data?.message || '执行失败')
  }
  executing.value = false
}

onMounted(loadData)
</script>

<style scoped>
.add-row {
  padding: 12px;
  border: 2px dashed #d9d9d9;
  border-radius: 4px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s;
}
.add-row:hover {
  border-color: #1890ff;
}
.item-row {
  display: flex;
  align-items: center;
  padding: 8px;
  margin-bottom: 4px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}
.item-row:hover {
  background: #f0f0f0;
}
</style>
