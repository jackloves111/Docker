<template>
  <div>
    <a-card title="Batch Combinations">
      <template #extra>
        <a-button type="primary" @click="showCreateModal">New Batch</a-button>
      </template>
      <a-table :dataSource="batches" :columns="columns" rowKey="id" :loading="loading">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span style="font-weight: 500;">{{ record.name }}</span>
          </template>
          <template v-if="column.key === 'items'">
            <a-tag v-for="item in (record.items || []).slice(0, 3)" :key="item.id" :color="getItemColor(item.item_type)" size="small">
              {{ getItemLabel(item.item_type) }} {{ getItemDisplayName(item) }}
            </a-tag>
            <a-tag v-if="(record.items || []).length > 3" size="small">+{{ record.items.length - 3 }}</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="showExecuteModal(record)">Execute</a-button>
              <a-popconfirm title="Delete?" @confirm="handleDelete(record.id)">
                <a-button type="link" danger size="small">Delete</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal v-model:open="executeModalVisible" title="Execute Batch" @ok="handleExecute" :confirmLoading="executing" width="700px">
      <VariableSelector :requiredVars="batchRequiredVars" @update:profileId="(val) => executeForm.profile_id = val" @update:overrides="(val) => executeOverrides = val" @update:valid="(val) => executeValid = val" />
      <a-divider style="margin: 12px 0" />
      <div style="display: flex; align-items: center; gap: 8px;">
        <a-switch v-model:checked="executeAutoReplace" />
        <span style="color: #666;">Auto-replace containers after pull/load</span>
      </div>
      <a-divider>Items</a-divider>
      <a-list :dataSource="executingBatch?.items || []" size="small">
        <template #renderItem="{ item, index }">
          <a-list-item>
            <a-tag :color="getItemColor(item.item_type)">{{ getItemLabel(item.item_type) }}</a-tag>
            <span style="margin-left: 8px;">{{ index + 1 }}. {{ getItemDisplayName(item) }}</span>
          </a-list-item>
        </template>
      </a-list>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { message } from "ant-design-vue"
import { batchesAPI, registriesAPI, projectsAPI } from "../api"
import VariableSelector from "../components/VariableSelector.vue"

const batches = ref([])
const registries = ref([])
const projects = ref([])
const loading = ref(false)
const executeModalVisible = ref(false)
const executing = ref(false)
const executingBatch = ref(null)
const executeForm = ref({ profile_id: null })
const executeOverrides = ref({})
const executeValid = ref(true)
const executeAutoReplace = ref(false)
const batchRequiredVars = ref([])
const resultModalVisible = ref(false)
const resultData = ref({ success: false, steps: [] })

const columns = [
  { title: "ID", dataIndex: "id", width: 60 },
  { title: "Name", dataIndex: "name", width: 200 },
  { title: "Items", key: "items" },
  { title: "Action", key: "action", width: 150 },
]

const getItemColor = (type) => ({ image_pull: "blue", image_load: "cyan", project_run: "green" }[type] || "default")
const getItemLabel = (type) => ({ image_pull: "Pull", image_load: "Load", project_run: "Run" }[type] || type)
const getItemDisplayName = (item) => {
  const config = typeof item.item_config === "string" ? JSON.parse(item.item_config) : item.item_config
  if (item.item_type === "image_pull") return config.image_name || "-"
  if (item.item_type === "image_load") return config.url ? (config.url.length > 30 ? config.url.substring(0, 27) + "..." : config.url) : "-"
  if (item.item_type === "project_run") { const p = projects.value.find(x => x.id === item.item_id); return p ? p.name : "#" + item.item_id }
  return "-"
}

const extractBatchVariables = (batch) => {
  const vars = new Set()
  const regex = /\$\{(\w+)\}|\$(\w+)/g
  for (const item of (batch.items || [])) {
    if (item.item_type === "project_run") {
      const project = projects.value.find(p => p.id === item.item_id)
      if (project) { const content = (project.command || "") + " " + (project.compose_content || ""); let match; while ((match = regex.exec(content)) !== null) { vars.add(match[1] || match[2]) } }
    }
  }
  return [...vars]
}

const loadData = async () => {
  loading.value = true
  try { const [b, r, p] = await Promise.all([batchesAPI.list(), registriesAPI.list(), projectsAPI.list()]); batches.value = b.data.data; registries.value = r.data.data; projects.value = p.data.data } catch (e) { message.error("Load failed") }
  loading.value = false
}

const showExecuteModal = (batch) => {
  executingBatch.value = batch; executeForm.value.profile_id = null; executeOverrides.value = {}; executeAutoReplace.value = false
  batchRequiredVars.value = extractBatchVariables(batch); executeModalVisible.value = true
}

const handleExecute = async () => {
  executing.value = true
  try {
    const res = await batchesAPI.execute(executingBatch.value.id, { profile_id: executeForm.value.profile_id, overrides: Object.keys(executeOverrides.value).length > 0 ? executeOverrides.value : undefined, auto_replace: executeAutoReplace.value })
    resultData.value = { success: res.data.data.success, steps: res.data.data.steps || [] }; resultModalVisible.value = true; executeModalVisible.value = false
  } catch (e) { message.error(e.response?.data?.message || "Failed") }
  executing.value = false
}

const handleDelete = async (id) => { try { await batchesAPI.delete(id); message.success("Deleted"); loadData() } catch (e) { message.error("Failed") } }

onMounted(loadData)
</script>