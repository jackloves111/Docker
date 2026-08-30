<template>
  <div>
    <a-card title="容器部署">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          新建部署
        </a-button>
      </template>

      <a-table :dataSource="projects" :columns="columns" rowKey="id" :loading="loading" :scroll="{ x: 820 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-tag :color="record.type === 'compose' ? 'blue' : 'green'">
              {{ record.type === 'compose' ? 'Compose' : 'Run' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'variables'">
            <template v-for="v in extractProjectVariables(record)" :key="v">
              <a-tag color="orange" style="margin-bottom: 2px;">{{ v }}</a-tag>
            </template>
            <span v-if="extractProjectVariables(record).length === 0" style="color: #999">-</span>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="editProject(record)">
                编辑
              </a-button>
              <a-button type="link" size="small" @click="showRunModal(record)">
                执行
              </a-button>
              <a-popconfirm
                title="确定删除此项目？"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingProject ? '编辑部署' : '新建部署'"
      @ok="handleSubmit"
      :confirmLoading="submitting"
      width="800px"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="部署名称" required>
          <a-input v-model:value="form.name" placeholder="My App" />
        </a-form-item>
        <a-form-item label="类型" required>
          <a-radio-group v-model:value="form.type">
            <a-radio value="run">Docker Run</a-radio>
            <a-radio value="compose">Docker Compose</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="form.type === 'run'" label="启动命令" required>
          <a-textarea
            v-model:value="form.command"
            :rows="4"
            placeholder="docker run -d --name myapp -p 80:80 nginx:latest"
          />
        </a-form-item>
        <a-form-item v-if="form.type === 'compose'" label="Compose 内容" required>
          <a-textarea
            v-model:value="form.compose_content"
            :rows="12"
            placeholder="version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - '80:80'"
          />
        </a-form-item>
        <a-form-item label="描述">
          <a-input v-model:value="form.description" placeholder="部署描述" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Run Modal -->
    <a-modal
      v-model:open="runModalVisible"
      title="执行项目"
      @ok="handleRun"
      :confirmLoading="running"
    >
      <VariableSelector
        :requiredVars="runRequiredVars"
        @update:profileId="(val) => runForm.profile_id = val"
        @update:overrides="(val) => runOverrides = val"
        @update:valid="(val) => runValid = val"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { projectsAPI } from '../api'
import VariableSelector from '../components/VariableSelector.vue'

const router = useRouter()
const projects = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const runModalVisible = ref(false)
const submitting = ref(false)
const running = ref(false)
const editingProject = ref(null)
const runningProject = ref(null)

const form = ref({
  name: '',
  type: 'run',
  command: '',
  compose_content: '',
  description: '',
})

const runForm = ref({
  profile_id: null,
})
const runOverrides = ref({})
const runValid = ref(true)
const runRequiredVars = ref([])

const columns = [
  { title: 'ID', dataIndex: 'id', width: 70, align: 'center' },
  { title: '名称', dataIndex: 'name', width: 200, ellipsis: true },
  { title: '类型', key: 'type', width: 100, align: 'center' },
  { title: '变量', key: 'variables', width: 200 },
  { title: '描述', dataIndex: 'description', ellipsis: true },
  { title: '操作', key: 'action', width: 250, fixed: 'right' },
]

const extractProjectVariables = (project) => {
  const content = (project.command || '') + ' ' + (project.compose_content || '')
  const regex = /\$\{(\w+)\}|\$(\w+)/g
  const vars = new Set()
  let match
  while ((match = regex.exec(content)) !== null) {
    vars.add(match[1] || match[2])
  }
  return [...vars]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await projectsAPI.list()
    projects.value = res.data.data
  } catch (e) {
    message.error('加载数据失败')
  }
  loading.value = false
}

const showCreateModal = () => {
  editingProject.value = null
  form.value = {
    name: '',
    type: 'run',
    command: '',
    compose_content: '',
    description: '',
  }
  modalVisible.value = true
}

const editProject = (project) => {
  editingProject.value = project
  form.value = {
    name: project.name,
    type: project.type,
    command: project.command || '',
    compose_content: project.compose_content || '',
    description: project.description || '',
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name) {
    message.warning('请输入部署名称')
    return
  }
  submitting.value = true
  try {
    if (editingProject.value) {
      await projectsAPI.update(editingProject.value.id, form.value)
      message.success('更新成功')
    } else {
      await projectsAPI.create(form.value)
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
    await projectsAPI.delete(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

const showRunModal = (project) => {
  runningProject.value = project
  runForm.value.profile_id = null
  runOverrides.value = {}
  runRequiredVars.value = extractProjectVariables(project)
  runModalVisible.value = true
}

const handleRun = async () => {
  running.value = true
  try {
    const params = {}
    if (runForm.value.profile_id) {
      params.profile_id = runForm.value.profile_id
    }
    if (Object.keys(runOverrides.value).length > 0) {
      params.overrides = runOverrides.value
    }
    const res = await projectsAPI.run(runningProject.value.id, params)
    if (res.data.data.result.success) {
      message.success('执行成功')
    } else {
      message.error(res.data.data.result.error || '执行失败')
    }
    runModalVisible.value = false
  } catch (e) {
    message.error(e.response?.data?.message || '执行失败')
  }
  running.value = false
}

onMounted(loadData)
</script>
