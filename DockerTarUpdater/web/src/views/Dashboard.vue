<template>
  <div class="dashboard">
    <h2>控制台</h2>

    <el-alert
      v-if="dockerConnected === false"
      title="Docker 连接失败"
      type="warning"
      description="无法连接到 Docker daemon，请检查容器是否正确映射了 /var/run/docker.sock"
      show-icon
      :closable="false"
      style="margin-bottom: 20px;"
    />

    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="12" :md="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.targets.total }}</div>
            <div class="stat-label">目标总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.targets.enabled }}</div>
            <div class="stat-label">已启用</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value success">{{ stats.tasks.success || 0 }}</div>
            <div class="stat-label">成功</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value danger">{{ stats.tasks.failed || 0 }}</div>
            <div class="stat-label">失败</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-tasks" shadow="hover">
      <template #header>
        <span>最近任务</span>
      </template>
      <el-table :data="recentTasks" style="width: 100%">
        <el-table-column prop="target_name" label="目标名称" width="150" />
        <el-table-column prop="action" label="操作" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" />
        <el-table-column prop="started_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.started_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { tasksAPI, dockerAPI } from '../api'

export default {
  name: 'Dashboard',
  setup() {
    const stats = ref({ targets: { total: 0, enabled: 0 }, tasks: { success: 0, failed: 0 } })
    const recentTasks = ref([])
    const dockerConnected = ref(null)

    const loadStats = async () => {
      try {
        const res = await tasksAPI.stats()
        stats.value = res.data
      } catch (e) {
        console.error(e)
      }
    }

    const loadRecentTasks = async () => {
      try {
        const res = await tasksAPI.latest()
        recentTasks.value = res.data
      } catch (e) {
        console.error(e)
      }
    }

    const getStatusType = (status) => {
      const map = { success: 'success', failed: 'danger', running: 'warning' }
      return map[status] || 'info'
    }

    const formatTime = (time) => {
      if (!time) return ''
      return new Date(time).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })
    }

    const checkDockerHealth = async () => {
      try {
        const res = await dockerAPI.health()
        dockerConnected.value = res.data.connected
      } catch (e) {
        dockerConnected.value = false
      }
    }

    onMounted(() => {
      loadStats()
      loadRecentTasks()
      checkDockerHealth()
    })

    return { stats, recentTasks, dockerConnected, getStatusType, formatTime }
  }
}
</script>

<style scoped>
.dashboard h2 { margin-bottom: 20px; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; padding: 10px; }
.stat-value { font-size: 36px; font-weight: bold; color: #409eff; }
.stat-value.success { color: #67c23a; }
.stat-value.danger { color: #f56c6c; }
.stat-label { font-size: 14px; color: #666; margin-top: 5px; }
.recent-tasks { margin-top: 20px; }
</style>
