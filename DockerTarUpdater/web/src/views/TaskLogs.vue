<template>
  <div class="task-logs">
    <h2>任务日志</h2>

    <el-card shadow="hover">
      <el-table :data="tasks" style="width: 100%" v-loading="loading" :table-layout="isMobile ? 'auto' : 'fixed'">
        <el-table-column prop="target_name" label="目标名称" min-width="100" />
        <el-table-column prop="action" label="操作" width="80" />
        <el-table-column prop="status" label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="120" show-overflow-tooltip />
        <el-table-column label="镜像" min-width="120">
          <template #default="{ row }">
            <span v-if="row.old_image_id">旧: {{ row.old_image_id.substring(0, 12) }}</span>
            <br v-if="row.old_image_id && row.new_image_id">
            <span v-if="row.new_image_id">新: {{ row.new_image_id.substring(0, 12) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="started_at" label="开始时间" width="140">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="finished_at" label="结束时间" width="140">
          <template #default="{ row }">
            {{ formatTime(row.finished_at) }}
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="70">
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
    const isMobile = ref(window.innerWidth < 768)

    window.addEventListener('resize', () => {
      isMobile.value = window.innerWidth < 768
    })

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
      return new Date(time).toLocaleString('zh-CN')
    }

    const getDuration = (start, end) => {
      if (!start || !end) return '-'
      const s = new Date(start)
      const e = new Date(end)
      const diff = Math.floor((e - s) / 1000)
      if (diff < 60) return `${diff}秒`
      if (diff < 3600) return `${Math.floor(diff / 60)}分${diff % 60}秒`
      return `${Math.floor(diff / 3600)}时${Math.floor((diff % 3600) / 60)}分`
    }

    onMounted(() => {
      loadTasks()
    })

    return { tasks, loading, isMobile, getStatusType, formatTime, getDuration }
  }
}
</script>

<style scoped>
h2 { margin-bottom: 20px; }
</style>
