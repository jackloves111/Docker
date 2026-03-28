import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import TargetList from '../views/TargetList.vue'
import TargetEdit from '../views/TargetEdit.vue'
import TaskLogs from '../views/TaskLogs.vue'
import Settings from '../views/Settings.vue'
import EnvEditor from '../views/EnvEditor.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/targets', name: 'Targets', component: TargetList },
  { path: '/targets/edit/:id?', name: 'TargetEdit', component: TargetEdit },
  { path: '/logs', name: 'Logs', component: TaskLogs },
  { path: '/settings', name: 'Settings', component: Settings },
  { path: '/env_editor', name: 'EnvEditor', component: EnvEditor }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
