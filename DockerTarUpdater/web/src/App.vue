<template>
  <div id="app">
    <el-container>
      <el-aside width="200px">
        <div class="logo">DockerTarUpdater</div>
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>Dashboard</span>
          </el-menu-item>
          <el-menu-item index="/targets">
            <el-icon><Box /></el-icon>
            <span>Targets</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>Logs</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>Settings</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header>
          <div class="header-content">
            <span class="scheduler-status">
              <el-tag :type="schedulerRunning ? 'success' : 'danger'">
                Scheduler: {{ schedulerRunning ? 'Running' : 'Stopped' }}
              </el-tag>
            </span>
            <el-button-group>
              <el-button v-if="!schedulerRunning" type="success" @click="startScheduler">Start</el-button>
              <el-button v-else type="warning" @click="stopScheduler">Stop</el-button>
              <el-button @click="syncScheduler">Sync</el-button>
            </el-button-group>
            <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="notification-badge">
              <el-button circle @click="showNotifications = true">
                <el-icon><Bell /></el-icon>
              </el-button>
            </el-badge>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>

    <el-dialog v-model="showNotifications" title="Notifications" width="500px">
      <el-scrollbar height="400px">
        <div v-for="notif in notifications" :key="notif.id" class="notification-item">
          <el-tag :type="getNotifType(notif.type)" size="small">{{ notif.type }}</el-tag>
          <strong>{{ notif.title }}</strong>
          <p>{{ notif.message }}</p>
          <small>{{ formatTime(notif.created_at) }}</small>
        </div>
        <el-empty v-if="notifications.length === 0" description="No notifications" />
      </el-scrollbar>
      <template #footer>
        <el-button @click="markAllRead">Mark All Read</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { schedulerAPI, notificationsAPI } from './api'

export default {
  name: 'App',
  setup() {
    const schedulerRunning = ref(false)
    const showNotifications = ref(false)
    const notifications = ref([])
    const unreadCount = ref(0)
    let pollInterval = null

    const loadSchedulerStatus = async () => {
      try {
        const res = await schedulerAPI.status()
        schedulerRunning.value = res.data.running
      } catch (e) {
        console.error(e)
      }
    }

    const loadNotifications = async () => {
      try {
        const res = await notificationsAPI.webList()
        notifications.value = res.data
        const countRes = await notificationsAPI.webUnreadCount()
        unreadCount.value = countRes.data.count
      } catch (e) {
        console.error(e)
      }
    }

    const startScheduler = async () => {
      await schedulerAPI.start()
      loadSchedulerStatus()
    }

    const stopScheduler = async () => {
      await schedulerAPI.stop()
      loadSchedulerStatus()
    }

    const syncScheduler = async () => {
      await schedulerAPI.sync()
      loadSchedulerStatus()
    }

    const markAllRead = async () => {
      await notificationsAPI.webRead()
      loadNotifications()
    }

    const getNotifType = (type) => {
      const map = { success: 'success', error: 'danger', warning: 'warning', info: 'info' }
      return map[type] || 'info'
    }

    const formatTime = (time) => {
      if (!time) return ''
      return new Date(time).toLocaleString()
    }

    onMounted(() => {
      loadSchedulerStatus()
      loadNotifications()
      pollInterval = setInterval(() => {
        loadNotifications()
      }, 5000)
    })

    onUnmounted(() => {
      if (pollInterval) clearInterval(pollInterval)
    })

    return {
      schedulerRunning,
      showNotifications,
      notifications,
      unreadCount,
      startScheduler,
      stopScheduler,
      syncScheduler,
      markAllRead,
      getNotifType,
      formatTime
    }
  }
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
.el-aside { background: #1a1a2e; }
.logo { color: #fff; padding: 20px; font-size: 18px; font-weight: bold; text-align: center; }
.el-menu { border: none; background: transparent; }
.el-menu-item { color: #fff; }
.el-menu-item:hover { background: #16213e; }
.el-header { background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; }
.header-content { display: flex; align-items: center; gap: 20px; width: 100%; }
.scheduler-status { margin-right: auto; }
.notification-badge { margin-left: 10px; }
.notification-item { padding: 10px; border-bottom: 1px solid #eee; }
.notification-item strong { display: block; margin: 5px 0; }
.notification-item p { margin: 5px 0; color: #666; font-size: 14px; }
.notification-item small { color: #999; }
</style>
