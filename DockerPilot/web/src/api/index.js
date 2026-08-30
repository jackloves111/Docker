import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Docker
export const dockerAPI = {
  health: () => api.get('/docker/health'),
  containers: () => api.get('/docker/containers'),
}

// Registries
export const registriesAPI = {
  list: () => api.get('/registries'),
  get: (id) => api.get(`/registries/${id}`),
  create: (data) => api.post('/registries', data),
  update: (id, data) => api.put(`/registries/${id}`, data),
  delete: (id) => api.delete(`/registries/${id}`),
}

// Images
export const imagesAPI = {
  list: () => api.get('/images'),
  pull: (data) => api.post('/images/pull', data),
  load: (data) => api.post('/images/load', data),
  loadUpload: (formData, onUploadProgress) => api.post('/images/load/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
    onUploadProgress,
  }),
  getTask: (taskId) => api.get(`/images/tasks/${taskId}`),
  getTasks: () => api.get('/images/tasks'),
  delete: (id) => api.delete(`/images/${id}`),
  tag: (id, repository, tag) => api.post(`/images/${id}/tag`, null, {
    params: { repository, tag }
  }),
  untag: (id, tag) => api.delete(`/images/${id}/untag`, {
    params: { tag }
  }),
  getManaged: () => api.get('/images/managed'),
}

// Projects
export const projectsAPI = {
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
  run: (id, params) => api.post(`/projects/${id}/run`, params.overrides || null, {
    params: { profile_id: params.profile_id }
  }),
  deployments: (id) => api.get(`/projects/${id}/deployments`),
  scanVariables: () => api.get('/projects/scan/variables'),
}

// Profiles
export const profilesAPI = {
  list: () => api.get('/profiles'),
  get: (id) => api.get(`/profiles/${id}`),
  create: (data) => api.post('/profiles', data),
  update: (id, data) => api.put(`/profiles/${id}`, data),
  delete: (id) => api.delete(`/profiles/${id}`),
  updateVariables: (id, data) => api.put(`/profiles/${id}/variables`, data),
}

// Batches
export const batchesAPI = {
  list: () => api.get('/batches'),
  get: (id) => api.get(`/batches/${id}`),
  create: (data) => api.post('/batches', data),
  update: (id, data) => api.put(`/batches/${id}`, data),
  delete: (id) => api.delete(`/batches/${id}`),
  addItem: (id, data) => api.post(`/batches/${id}/items`, data),
  reorderItems: (id, data) => api.put(`/batches/${id}/items/reorder`, data),
  updateItem: (groupId, itemId, data) => api.put(`/batches/${groupId}/items/${itemId}`, data),
  deleteItem: (id, itemId) => api.delete(`/batches/${id}/items/${itemId}`),
  preview: (id, profileId) => api.get(`/batches/${id}/execute/preview`, { params: { profile_id: profileId } }),
  execute: (id, data) => api.post(`/batches/${id}/execute`, data),
  executions: (id) => api.get(`/batches/${id}/executions`),
}

// Containers
export const containersAPI = {
  list: () => api.get('/containers'),
  get: (id) => api.get(`/containers/${id}`),
  logs: (id, tail = 100) => api.get(`/containers/${id}/logs`, { params: { tail } }),
  stop: (id) => api.post(`/containers/${id}/stop`),
  start: (id) => api.post(`/containers/${id}/start`),
  remove: (id) => api.delete(`/containers/${id}`),
  replace: (id) => api.post(`/containers/${id}/replace`),
  findByImage: (imageTag) => api.get(`/containers/by-image/${encodeURIComponent(imageTag)}`),
}

// Settings
export const settingsAPI = {
  get: (key) => api.get(`/settings/${key}`),
  getAll: () => api.get('/settings'),
  set: (key, value) => api.put(`/settings/${key}`, { key, value }),
}

export default api
