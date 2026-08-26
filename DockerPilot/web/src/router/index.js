import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/images',
    name: 'images',
    component: () => import('../views/ImageManager.vue'),
  },
  {
    path: '/projects',
    name: 'projects',
    component: () => import('../views/ProjectManager.vue'),
  },
  {
    path: '/projects/:id/edit',
    name: 'projectEdit',
    component: () => import('../views/ProjectEdit.vue'),
  },
  {
    path: '/batches',
    name: 'batches',
    component: () => import('../views/BatchManager.vue'),
  },
  {
    path: '/containers',
    name: 'containers',
    component: () => import('../views/ContainerManager.vue'),
  },
  {
    path: '/logs',
    name: 'logs',
    component: () => import('../views/Logs.vue'),
  },
  {
    path: '/registries',
    name: 'registries',
    component: () => import('../views/Registries.vue'),
  },
  {
    path: '/profiles',
    name: 'profiles',
    component: () => import('../views/Profiles.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
