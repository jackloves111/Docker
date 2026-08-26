<template>
  <div>
    <a-card title="镜像源配置">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">
          添加镜像源
        </a-button>
      </template>

      <a-table :dataSource="registries" :columns="columns" rowKey="id" :loading="loading">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'is_default'">
            <a-switch
              :checked="record.is_default"
              @change="(val) => handleSetDefault(record.id, val)"
            />
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="editRegistry(record)">
                编辑
              </a-button>
              <a-popconfirm
                title="确定删除此镜像源？"
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
      :title="editingRegistry ? '编辑镜像源' : '添加镜像源'"
      @ok="handleSubmit"
      :confirmLoading="submitting"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="form.name" placeholder="阿里云镜像源" />
        </a-form-item>
        <a-form-item label="地址" required>
          <a-input v-model:value="form.url" placeholder="registry.cn-hangzhou.aliyuncs.com" />
        </a-form-item>
        <a-form-item label="用户名">
          <a-input v-model:value="form.username" placeholder="可选" />
        </a-form-item>
        <a-form-item label="密码">
          <a-input-password v-model:value="form.password" placeholder="可选" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { registriesAPI } from '../api'

const registries = ref([])
const loading = ref(false)
const modalVisible = ref(false)
const submitting = ref(false)
const editingRegistry = ref(null)

const form = ref({
  name: '',
  url: '',
  username: '',
  password: '',
})

const columns = [
  { title: 'ID', dataIndex: 'id', width: 80 },
  { title: '名称', dataIndex: 'name', width: 150 },
  { title: '地址', dataIndex: 'url', width: 300 },
  { title: '默认', key: 'is_default', width: 100 },
  { title: '操作', key: 'action', width: 150 },
]

const loadData = async () => {
  loading.value = true
  try {
    const res = await registriesAPI.list()
    registries.value = res.data.data
  } catch (e) {
    message.error('加载数据失败')
  }
  loading.value = false
}

const showCreateModal = () => {
  editingRegistry.value = null
  form.value = {
    name: '',
    url: '',
    username: '',
    password: '',
  }
  modalVisible.value = true
}

const editRegistry = (registry) => {
  editingRegistry.value = registry
  form.value = {
    name: registry.name,
    url: registry.url,
    username: registry.username || '',
    password: registry.password || '',
  }
  modalVisible.value = true
}

const handleSubmit = async () => {
  if (!form.value.name || !form.value.url) {
    message.warning('请填写名称和地址')
    return
  }
  submitting.value = true
  try {
    if (editingRegistry.value) {
      await registriesAPI.update(editingRegistry.value.id, form.value)
      message.success('更新成功')
    } else {
      await registriesAPI.create(form.value)
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
    await registriesAPI.update(id, { is_default: checked })
    message.success('设置成功')
    loadData()
  } catch (e) {
    message.error('设置失败')
  }
}

const handleDelete = async (id) => {
  try {
    await registriesAPI.delete(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(loadData)
</script>
