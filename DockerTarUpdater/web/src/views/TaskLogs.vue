<template>
  <div class="task-logs">
    <h2>Task Logs</h2>

    <el-card shadow="hover">
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="target_name" label="Target" width="150" />
        <el-table-column prop="action" label="Action" width="120" />
        <el-table-column prop="status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="Message" show-overflow-tooltip />
        <el-table-column label="Images" width="200">
          <template #default="{ row }">
            <span v-if="row.old_image_id">Old: {{ row.old_image_id.substring(0, 12) }}</span>
            <br v-if="row.old_image_id && row.new_image_id">
            <span v-if="row.new_image_id">New: {{ row.new_image_id.substring(0, 12) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="Started" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="finished_at" label="Finished" width="180">
          <template #default="{ row }">
            {{ formatTime(row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="Duration" width="100">
          <template #default="{ row }">
            {{ getDuration(row.started_at, row.finished_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { tasksAPI } from '../api'

export default {
  name: 'TaskLogs',
  setup() {
    const tasks = ref([])
    const loading = ref(false)

    const loadTasks = async () => {
      loading.value = true
      try {
        const res = await tasksAPI.list(100)
        tasks.value = res.data
      } catch (e) {
        console.error(e)
      } finally {
        loading.value = false
      }
    }

    const getStatusType = (status) => {
      const map = { success: 'success', failed: 'danger', running: 'warning' }
      return map[status] || 'info'
    }

    const formatTime = (time) => {
      if (!time) return '-'
      return new Date(time).toLocaleString()
    }

    const getDuration = (start, end) => {
      if (!start || !end) return '-'
      const s = new Date(start)
      const e = new Date(end)
      const diff = Math.floor((e - s) / 1000)
      if (diff < 60) return `${diff}s`
      if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`
      return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`
    }

    onMounted(() => {
      loadTasks()
    })

    return { tasks, loading, getStatusType, formatTime, getDuration }
  }
}
</script>

<style scoped>
h2 { margin-bottom: 20px; }
</style>
