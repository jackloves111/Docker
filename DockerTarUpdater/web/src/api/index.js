import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const targetsAPI = {
  list: () => api.get('/targets'),
  get: (id) => api.get(`/targets/${id}`),
  create: (data) => api.post('/targets', data),
  update: (id, data) => api.put(`/targets/${id}`, data),
  delete: (id) => api.delete(`/targets/${id}`),
  trigger: (id) => api.post(`/targets/${id}/trigger`),
  getInfo: (id) => api.get(`/targets/${id}/info`),
  listContainers: () => api.get('/targets/containers')
}

export const tasksAPI = {
  list: (limit) => api.get('/tasks', { params: { limit } }),
  get: (id) => api.get(`/tasks/${id}`),
  latest: () => api.get('/tasks/latest'),
  byTarget: (id, limit) => api.get(`/tasks/target/${id}`, { params: { limit } }),
  stats: () => api.get('/tasks/stats')
}

export const schedulerAPI = {
  status: () => api.get('/scheduler/status'),
  start: () => api.post('/scheduler/start'),
  stop: () => api.post('/scheduler/stop'),
  sync: () => api.post('/scheduler/sync')
}

export const notificationsAPI = {
  list: () => api.get('/notifications'),
  create: (data) => api.post('/notifications', data),
  update: (id, data) => api.put(`/notifications/${id}`, data),
  delete: (id) => api.delete(`/notifications/${id}`),
  webList: () => api.get('/notifications/web/list'),
  webUnread: () => api.get('/notifications/web/unread'),
  webUnreadCount: () => api.get('/notifications/web/unread/count'),
  webRead: (ids) => api.put('/notifications/web/read', { ids })
}

export const dockerAPI = {
  health: () => api.get('/docker/health')
}

export const envEditorAPI = {
  files: () => api.get('/env_editor/files'),
  env: (path) => api.get('/env_editor/env', { params: { path } }),
  save: (path, entries, upserts) => api.put('/env_editor/env', { path, entries, upserts })
}

export default api
