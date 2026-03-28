<template>
  <div class="settings">
    <h2>Settings</h2>

    <el-card class="settings-card" shadow="hover">
      <template #header>
        <span>Notifications</span>
        <el-button type="primary" size="small" @click="addNotification">Add</el-button>
      </template>

      <el-table :data="notifications" style="width: 100%">
        <el-table-column prop="name" label="Name" width="150" />
        <el-table-column prop="type" label="Type" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="Enabled" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? 'Yes' : 'No' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="150">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="deleteNotification(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAddDialog" title="Add Notification" width="500px">
      <el-form :model="newNotif" label-width="100px">
        <el-form-item label="Name">
          <el-input v-model="newNotif.name" placeholder="My DingTalk" />
        </el-form-item>
        <el-form-item label="Type">
          <el-select v-model="newNotif.type" placeholder="Select type">
            <el-option label="Web" value="web" />
            <el-option label="DingTalk" value="dingtalk" />
            <el-option label="FeiShu" value="feishu" />
            <el-option label="Email" value="email" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="newNotif.type === 'dingtalk'" label="Webhook">
          <el-input v-model="newNotif.config.webhook" placeholder="DingTalk webhook URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createNotification">Create</el-button>
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
        ElMessage.success('Created')
        showAddDialog.value = false
        loadNotifications()
      } catch (e) {
        ElMessage.error('Failed to create')
      }
    }

    const deleteNotification = async (row) => {
      try {
        await ElMessageBox.confirm('Delete this notification?', 'Warning', { type: 'warning' })
        await notificationsAPI.delete(row.id)
        ElMessage.success('Deleted')
        loadNotifications()
      } catch (e) {
        if (e !== 'cancel') ElMessage.error('Failed to delete')
      }
    }

    onMounted(() => {
      loadNotifications()
    })

    return { notifications, showAddDialog, newNotif, addNotification, createNotification, deleteNotification }
  }
}
</script>

<style scoped>
h2 { margin-bottom: 20px; }
.settings-card { margin-bottom: 20px; }
</style>
