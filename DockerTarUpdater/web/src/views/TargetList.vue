<template>
  <div class="target-list">
    <div class="toolbar">
      <h2>升级目标</h2>
      <el-button type="primary" @click="$router.push('/targets/edit')">添加目标</el-button>
    </div>

    <el-table :data="targets" style="width: 100%" v-loading="loading" :table-layout="isMobile ? 'auto' : 'fixed'">
      <el-table-column prop="name" label="目标名称/标识" min-width="120" />
      <el-table-column prop="tar_url" label="Tar URL" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.tar_url }}
          <el-tag v-if="row.url_type === 'api'" type="warning" size="small" style="margin-left: 4px">API</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="image_tag" label="镜像标签" min-width="120" />
      <el-table-column prop="schedule_type" label="调度类型" width="100">
        <template #default="{ row }">
          {{ row.schedule_type === 'cron' ? 'Cron' : row.schedule_type === 'manual' ? '手动' : '间隔' }}
        </template>
      </el-table-column>
      <el-table-column prop="schedule_value" label="调度值" width="100" />
      <el-table-column prop="enabled" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_update_status" label="最后更新" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.last_update_status" :type="getStatusType(row.last_update_status)">
            {{ row.last_update_status }}
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="auto" min-width="220">
        <template #default="{ row }">
          <el-button size="small" @click="viewInfo(row)">详情</el-button>
          <el-button size="small" type="primary" @click="$router.push(`/targets/edit/${row.id}`)">编辑</el-button>
          <el-button size="small" type="warning" @click="triggerUpgrade(row)" :loading="row.upgrading">触发</el-button>
          <el-button size="small" type="danger" @click="deleteTarget(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showInfo" title="匹配的容器信息" width="800px">
      <div v-if="containerInfo && containerInfo.length > 0">
        <el-table :data="containerInfo" border>
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="image" label="镜像" />
          <el-table-column prop="image_id" label="镜像ID" show-overflow-tooltip />
        </el-table>
      </div>
      <el-empty v-else description="未找到匹配的容器" />
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
    const isMobile = ref(window.innerWidth < 768)

    window.addEventListener('resize', () => {
      isMobile.value = window.innerWidth < 768
    })

    const loadTargets = async () => {
      loading.value = true
      try {
        const res = await targetsAPI.list()
        targets.value = res.data.map(t => ({ ...t, upgrading: false }))
      } catch (e) {
        ElMessage.error('加载目标失败')
      } finally {
        loading.value = false
      }
    }

    const viewInfo = async (row) => {
      try {
        const res = await targetsAPI.getInfo(row.id)
        containerInfo.value = res.data.containers || []
        showInfo.value = true
      } catch (e) {
        containerInfo.value = []
        showInfo.value = true
      }
    }

    const triggerUpgrade = async (row) => {
      row.upgrading = true
      try {
        await targetsAPI.trigger(row.id)
        ElMessage.success('升级已触发')
      } catch (e) {
        ElMessage.error('触发升级失败')
      } finally {
        setTimeout(() => { row.upgrading = false }, 3000)
      }
    }

    const deleteTarget = async (row) => {
      try {
        await ElMessageBox.confirm('确定要删除此目标吗？', '警告', {
          type: 'warning'
        })
        await targetsAPI.delete(row.id)
        ElMessage.success('删除成功')
        loadTargets()
      } catch (e) {
        if (e !== 'cancel') ElMessage.error('删除失败')
      }
    }

    const getStatusType = (status) => {
      const map = { success: 'success', failed: 'danger', running: 'warning' }
      return map[status] || 'info'
    }

    onMounted(() => {
      loadTargets()
    })

    return { targets, loading, showInfo, containerInfo, isMobile, viewInfo, triggerUpgrade, deleteTarget, getStatusType }
  }
}
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.toolbar h2 { margin: 0; }
</style>
