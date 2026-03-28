import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import TargetList from '../views/TargetList.vue'
import TargetEdit from '../views/TargetEdit.vue'
import TaskLogs from '../views/TaskLogs.vue'
import Settings from '../views/Settings.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/targets', name: 'Targets', component: TargetList },
  { path: '/targets/edit/:id?', name: 'TargetEdit', component: TargetEdit },
  { path: '/logs', name: 'Logs', component: TaskLogs },
  { path: '/settings', name: 'Settings', component: Settings }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
