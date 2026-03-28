<template>
  <div class="target-list">
    <div class="toolbar">
      <h2>Upgrade Targets</h2>
      <el-button type="primary" @click="$router.push('/targets/edit')">Add Target</el-button>
    </div>

    <el-table :data="targets" style="width: 100%" v-loading="loading">
      <el-table-column prop="name" label="Container Name" width="150" />
      <el-table-column prop="tar_url" label="Tar URL" show-overflow-tooltip />
      <el-table-column prop="image_tag" label="Image Tag" width="180" />
      <el-table-column prop="schedule_type" label="Schedule Type" width="120">
        <template #default="{ row }">
          {{ row.schedule_type === 'cron' ? 'Cron' : 'Interval' }}
        </template>
      </el-table-column>
      <el-table-column prop="schedule_value" label="Schedule" width="120" />
      <el-table-column prop="enabled" label="Status" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Enabled' : 'Disabled' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_update_status" label="Last Update" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.last_update_status" :type="getStatusType(row.last_update_status)">
            {{ row.last_update_status }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="viewInfo(row)">Info</el-button>
          <el-button size="small" type="primary" @click="$router.push(`/targets/edit/${row.id}`)">Edit</el-button>
          <el-button size="small" type="warning" @click="triggerUpgrade(row)" :loading="row.upgrading">Trigger</el-button>
          <el-button size="small" type="danger" @click="deleteTarget(row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showInfo" title="Container Info" width="600px">
      <el-descriptions v-if="containerInfo" :column="2" border>
        <el-descriptions-item label="Name">{{ containerInfo.name }}</el-descriptions-item>
        <el-descriptions-item label="Status">{{ containerInfo.status }}</el-descriptions-item>
        <el-descriptions-item label="Image">{{ containerInfo.image }}</el-descriptions-item>
        <el-descriptions-item label="Image ID">{{ containerInfo.image_id }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="Container not found or not running" />
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { targetsAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'TargetList',
  setup() {
    const targets = ref([])
    const loading = ref(false)
    const showInfo = ref(false)
    const containerInfo = ref(null)

    const loadTargets = async () => {
      loading.value = true
      try {
        const res = await targetsAPI.list()
        targets.value = res.data.map(t => ({ ...t, upgrading: false }))
      } catch (e) {
        ElMessage.error('Failed to load targets')
      } finally {
        loading.value = false
      }
    }

    const viewInfo = async (row) => {
      try {
        const res = await targetsAPI.getInfo(row.id)
        containerInfo.value = res.data
        showInfo.value = true
      } catch (e) {
        containerInfo.value = null
        showInfo.value = true
      }
    }

    const triggerUpgrade = async (row) => {
      row.upgrading = true
      try {
        await targetsAPI.trigger(row.id)
        ElMessage.success('Upgrade triggered')
      } catch (e) {
        ElMessage.error('Failed to trigger upgrade')
      } finally {
        setTimeout(() => { row.upgrading = false }, 3000)
      }
    }

    const deleteTarget = async (row) => {
      try {
        await ElMessageBox.confirm('Are you sure to delete this target?', 'Warning', {
          type: 'warning'
        })
        await targetsAPI.delete(row.id)
        ElMessage.success('Deleted')
        loadTargets()
      } catch (e) {
        if (e !== 'cancel') ElMessage.error('Failed to delete')
      }
    }

    const getStatusType = (status) => {
      const map = { success: 'success', failed: 'danger', running: 'warning' }
      return map[status] || 'info'
    }

    onMounted(() => {
      loadTargets()
    })

    return { targets, loading, showInfo, containerInfo, viewInfo, triggerUpgrade, deleteTarget, getStatusType }
  }
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.toolbar h2 { margin: 0; }
</style>
