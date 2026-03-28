<template>
  <div id="app">
    <div v-if="isMobile && !isCollapse" class="sidebar-overlay" @click="isCollapse = true"></div>
    <el-container class="app-container">
      <el-aside :class="['sidebar', { 'v-hidden': isCollapse }]">
        <div class="logo">
          <el-icon v-if="isCollapse" :size="24"><Box /></el-icon>
          <span v-else>Docker镜像更新器</span>
        </div>
        <el-menu :default-active="$route.path" router :collapse="isCollapse" :collapse-transition="false">
          <el-menu-item index="/">
            <el-icon><HomeFilled /></el-icon>
            <span>控制台</span>
          </el-menu-item>
          <el-menu-item index="/targets">
            <el-icon><Box /></el-icon>
            <span>升级目标</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>任务日志</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>设置</span>
          </el-menu-item>
          <el-menu-item index="/env_editor">
            <el-icon><Edit /></el-icon>
            <span>环境编辑器</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header>
          <div class="header-content">
            <el-button text @click="isCollapse = !isCollapse" class="collapse-btn">
              <el-icon :size="20"><Expand v-if="isCollapse" /><Fold v-else /></el-icon>
            </el-button>
            <span class="scheduler-status">
              <el-tag :type="schedulerRunning ? 'success' : 'danger'">
                调度器: {{ schedulerRunning ? '运行中' : '已停止' }}
              </el-tag>
            </span>
            <el-button-group>
              <el-button v-if="!schedulerRunning" type="success" @click="startScheduler">启动</el-button>
              <el-button v-else type="warning" @click="stopScheduler">停止</el-button>
              <el-button @click="syncScheduler">同步</el-button>
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

    <el-dialog v-model="showNotifications" title="通知中心" width="500px">
      <el-scrollbar height="400px">
        <div v-for="notif in notifications" :key="notif.id" class="notification-item">
          <el-tag :type="getNotifType(notif.type)" size="small">{{ notif.type }}</el-tag>
          <strong>{{ notif.title }}</strong>
          <p>{{ notif.message }}</p>
          <small>{{ formatTime(notif.created_at) }}</small>
        </div>
        <el-empty v-if="notifications.length === 0" description="暂无通知" />
      </el-scrollbar>
      <template #footer>
        <el-button @click="markAllRead">全部标记为已读</el-button>
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
    const isCollapse = ref(false)
    const schedulerRunning = ref(false)
    const showNotifications = ref(false)
    const notifications = ref([])
    const unreadCount = ref(0)
    let pollInterval = null

    const isMobile = ref(window.innerWidth < 768)

    const updateMobile = () => {
      isMobile.value = window.innerWidth < 768
    }

    onMounted(() => {
      window.addEventListener('resize', updateMobile)
    })

    onUnmounted(() => {
      window.removeEventListener('resize', updateMobile)
      if (pollInterval) clearInterval(pollInterval)
    })

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
      return new Date(time).toLocaleString('zh-CN')
    }

    onMounted(() => {
      loadSchedulerStatus()
      loadNotifications()
      pollInterval = setInterval(() => {
        loadNotifications()
      }, 5000)
    })

    return {
      isMobile,
      isCollapse,
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
.app-container { height: 100%; }
.sidebar { background: #1a1a2e; height: 100%; transition: transform 0.3s, width 0.3s; }
.logo { color: #fff; padding: 20px 10px; font-size: 16px; font-weight: bold; text-align: center; white-space: nowrap; overflow: hidden; }
.el-menu { border: none; background: transparent; }
.el-menu-item { color: #fff; }
.el-menu-item:hover { background: #16213e; }
.el-header { background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center; }
.header-content { display: flex; align-items: center; gap: 12px; width: 100%; }
.scheduler-status { margin-right: auto; }
.notification-badge { margin-left: 10px; }
.notification-item { padding: 10px; border-bottom: 1px solid #eee; }
.notification-item strong { display: block; margin: 5px 0; }
.notification-item p { margin: 5px 0; color: #666; font-size: 14px; }
.notification-item small { color: #999; }
.collapse-btn { padding: 8px; }
.sidebar-overlay { position: fixed; left: 0; right: 0; top: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 999; }

@media (min-width: 769px) {
  .sidebar { width: 200px; }
  .sidebar.v-hidden { width: 64px; }
}

@media (max-width: 768px) {
  .sidebar { position: fixed; left: 0; top: 0; bottom: 0; z-index: 1000; transform: translateX(0); width: 200px !important; }
  .sidebar.v-hidden { transform: translateX(-100%); }
  .el-header { padding-left: 10px; }
  .header-content { gap: 8px; }
  .scheduler-status { font-size: 12px; }
}
</style>
