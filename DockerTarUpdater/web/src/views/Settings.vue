<template>
  <div class="settings">
    <h2>设置</h2>

    <el-card class="settings-card" shadow="hover">
      <template #header>
        <span>通知配置</span>
        <el-button type="primary" size="small" @click="addNotification">添加</el-button>
      </template>

      <el-table :data="notifications" style="width: 100%" :table-layout="isMobile ? 'auto' : 'fixed'">
        <el-table-column prop="name" label="名称" min-width="100" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="auto" min-width="100">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="deleteNotification(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAddDialog" title="添加通知" width="500px">
      <el-form :model="newNotif" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="newNotif.name" placeholder="我的钉钉" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="newNotif.type" placeholder="选择类型">
            <el-option label="Web" value="web" />
            <el-option label="钉钉" value="dingtalk" />
            <el-option label="飞书" value="feishu" />
            <el-option label="邮件" value="email" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="newNotif.type === 'dingtalk'" label="Webhook">
          <el-input v-model="newNotif.config.webhook" placeholder="钉钉 Webhook URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createNotification">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { notificationsAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Settings',
  setup() {
    const notifications = ref([])
    const showAddDialog = ref(false)
    const newNotif = ref({
      name: '',
      type: 'web',
      config: { webhook: '' }
    })
    const isMobile = ref(window.innerWidth < 768)

    window.addEventListener('resize', () => {
      isMobile.value = window.innerWidth < 768
    })

    const loadNotifications = async () => {
      try {
        const res = await notificationsAPI.list()
        notifications.value = res.data
      } catch (e) {
        console.error(e)
      }
    }

    const addNotification = () => {
      newNotif.value = { name: '', type: 'web', config: { webhook: '' } }
      showAddDialog.value = true
    }

    const createNotification = async () => {
      try {
        await notificationsAPI.create(newNotif.value)
        ElMessage.success('创建成功')
        showAddDialog.value = false
        loadNotifications()
      } catch (e) {
        ElMessage.error('创建失败')
      }
    }

    const deleteNotification = async (row) => {
      try {
        await ElMessageBox.confirm('确定要删除此通知吗？', '警告', { type: 'warning' })
        await notificationsAPI.delete(row.id)
        ElMessage.success('删除成功')
        loadNotifications()
      } catch (e) {
        if (e !== 'cancel') ElMessage.error('删除失败')
      }
    }

    onMounted(() => {
      loadNotifications()
    })

    return { notifications, showAddDialog, newNotif, isMobile, addNotification, createNotification, deleteNotification }
  }
}
</script>

<style scoped>
h2 { margin-bottom: 20px; }
.settings-card { margin-bottom: 20px; }
</style>
