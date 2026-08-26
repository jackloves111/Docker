<template>
  <div>
    <a-card title="路径变量方案">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          新建方案
        </a-button>
      </template>

      <a-row :gutter="16">
        <a-col :span="8" v-for="profile in profiles" :key="profile.id">
          <a-card :title="profile.name" style="margin-bottom: 16px">
            <template #extra>
              <a-space>
                <a-switch
                  :checked="profile.is_default"
                  checkedText="默认"
                  unCheckedText=""
                  @change="(val) => handleSetDefault(profile.id, val)"
                />
                <a-button type="link" size="small" @click="editProfile(profile)">
                  编辑
                </a-button>
                <a-popconfirm
                  title="确定删除此方案？"
                  @confirm="handleDelete(profile.id)"
                >
                  <a-button type="link" danger size="small">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>

            <a-list :dataSource="profile.variables" size="small">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <span style="font-family: monospace">{{ item.var_name }}</span>
                    </template>
                    <template #description>
                      <span style="font-family: monospace">{{ item.var_value }}</span>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
              <template #empty>
                <a-empty description="暂无变量" />
              </template>
            </a-list>
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingProfile ? '编辑方案' : '新建方案'"
      @ok="handleSubmit"
      :confirmLoading="submitting"
      width="600px"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="方案名称" required>
          <a-input v-model:value="form.name" placeholder="本地硬盘部署" />
        </a-form-item>

        <a-divider>变量列表</a-divider>

        <!-- 自动识别变量 -->
        <a-alert
          v-if="scannedVars.length > 0 && !editingProfile"
          type="info"
          showIcon
          style="margin-bottom: 16px"
        >
          <template #message>
            从项目中识别到 {{ scannedVars.length }} 个变量
          </template>
          <template #description>
            <div style="margin-top: 8px">
              <a-checkbox-group v-model:value="selectedScannedVars" :options="scannedVars.map(v => ({
                label: `${v.name}（${v.count}个项目使用）`,
                value: v.name
              }))" />
            </div>
            <a-button
              type="primary"
              size="small"
              style="margin-top: 8px"
              @click="addScannedVars"
              :disabled="selectedScannedVars.length === 0"
            >
              添加选中变量
            </a-button>
          </template>
        </a-alert>

        <div v-for="(variable, index) in form.variables" :key="index" style="margin-bottom: 8px">
          <a-row :gutter="8">
            <a-col :span="6">
              <a-input
                v-model:value="variable.var_name"
                placeholder="变量名"
                style="font-family: monospace"
              />
            </a-col>
            <a-col :span="14">
              <a-input
                v-model:value="variable.var_value"
                placeholder="值，如 /data"
                style="font-family: monospace"
              />
            </a-col>
            <a-col :span="4">
              <a-button danger @click="removeVariable(index)">删除</a-button>
            </a-col>
          </a-row>
        </div>

        <a-button type="dashed" block @click="addVariable">
          + 添加变量
        </a-button>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { profilesAPI, projectsAPI } from '../api'

const profiles = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const submitting = ref(false)
const editingProfile = ref(null)
const scannedVars = ref([])
const selectedScannedVars = ref([])

const form = ref({
  name: '',
  variables: [{ var_name: '', var_value: '', description: '' }],
})

// Load variables scanned from projects
const loadScannedVars = async () => {
  try {
    const res = await projectsAPI.scanVariables()
    scannedVars.value = res.data.data || []
  } catch (e) {
    console.error('Failed to scan variables:', e)
  }
}

// Add selected scanned variables to form
const addScannedVars = () => {
  selectedScannedVars.value.forEach(name => {
    // Don't add if already exists
    if (!form.value.variables.some(v => v.var_name === name)) {
      form.value.variables.push({ var_name: name, var_value: '', description: '' })
    }
  })
  message.success(`已添加 ${selectedScannedVars.value.length} 个变量`)
  selectedScannedVars.value = []
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await profilesAPI.list()
    profiles.value = res.data.data
  } catch (e) {
    message.error('加载数据失败')
  }
  loading.value = false
}

const showCreateModal = () => {
  editingProfile.value = null
  form.value = {
    name: '',
    variables: [{ var_name: '', var_value: '', description: '' }],
  }
  scannedVars.value = []
  selectedScannedVars.value = []
  modalVisible.value = true
  loadScannedVars()
}

const editProfile = (profile) => {
  editingProfile.value = profile
  form.value = {
    name: profile.name,
    variables: profile.variables.map(v => ({
      var_name: v.var_name,
      var_value: v.var_value,
      description: v.description || '',
    })),
  }
  modalVisible.value = true
}

const addVariable = () => {
  form.value.variables.push({ var_name: '', var_value: '', description: '' })
}

const removeVariable = (index) => {
  form.value.variables.splice(index, 1)
}

const handleSubmit = async () => {
  if (!form.value.name) {
    message.warning('请输入方案名称')
    return
  }

  // Filter out empty variables
  const variables = form.value.variables.filter(v => v.var_name && v.var_value)

  submitting.value = true
  try {
    if (editingProfile.value) {
      await profilesAPI.update(editingProfile.value.id, {
        name: form.value.name,
      })
      await profilesAPI.updateVariables(editingProfile.value.id, { variables })
      message.success('更新成功')
    } else {
      await profilesAPI.create({
        name: form.value.name,
        variables,
      })
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (e) {
    message.error(e.response?.data?.message || '操作失败')
  }
  submitting.value = false
}

const handleSetDefault = async (id, checked) => {
  try {
    await profilesAPI.update(id, { is_default: checked })
    message.success('设置成功')
    loadData()
  } catch (e) {
    message.error('设置失败')
  }
}

const handleDelete = async (id) => {
  try {
    await profilesAPI.delete(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(loadData)
</script>
