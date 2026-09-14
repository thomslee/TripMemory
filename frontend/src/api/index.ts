import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('tm_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('tm_token')
      localStorage.removeItem('tm_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 认证API
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', new URLSearchParams({ username, password })),
  register: (username: string, password: string, nickname?: string) =>
    api.post('/auth/register', null, { params: { username, password, nickname } }),
  me: () => api.get('/auth/me'),
  // TripCanvas 账号绑定（同步行程时使用绑定账号访问 TripCanvas）
  getTripCanvasBinding: () => api.get('/auth/tripcanvas-binding'),
  bindTripCanvas: (tripcanvasUsername: string, tripcanvasPassword: string) =>
    api.put('/auth/tripcanvas-binding', { tripcanvas_username: tripcanvasUsername, tripcanvas_password: tripcanvasPassword }),
  unbindTripCanvas: () => api.delete('/auth/tripcanvas-binding'),
  changePassword: (oldPassword: string, newPassword: string) =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),
}

// 应用设置API（管理员）：大模型等外部接口配置
export const settingsApi = {
  get: () => api.get('/settings'),
  update: (data: any) => api.put('/settings', data),
}

// 管理员API：用户管理
export const adminApi = {
  listUsers: () => api.get('/admin/users'),
  updateRole: (userId: number, role: string) => api.patch(`/admin/users/${userId}`, { role }),
}

// 记忆行程API
export const memoryApi = {
  list: () => api.get('/memory/trips'),
  detail: (id: number) => api.get(`/memory/trips/${id}`),
  syncFromTripCanvas: (tripcanvasTripId: number) =>
    api.post(`/memory/sync-from-tripcanvas/${tripcanvasTripId}`),
  matchPhotos: (id: number) => api.post(`/memory/trips/${id}/match-photos`),
  // 照片上传（本地/图库精选照片，multipart 多文件）
  uploadPhotos: (tripId: number, files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return api.post(`/memory/trips/${tripId}/photos/upload`, form)
  },
  // 手动关联照片到节点（nodeId=0 取消关联）
  assignPhoto: (tripId: number, photoId: number, nodeId: number) =>
    api.put(`/memory/trips/${tripId}/photos/${photoId}/assign`, null, { params: { node_id: nodeId } }),
  // 删除照片（照片库）
  deletePhoto: (tripId: number, photoId: number) =>
    api.delete(`/memory/trips/${tripId}/photos/${photoId}`),
  generateArticle: (tripId: number, nodeId: number) =>
    api.post(`/memory/trips/${tripId}/nodes/${nodeId}/generate-article`),
  generateTTS: (tripId: number, nodeId: number, voice: string = 'xiaoxiao') =>
    api.post(`/memory/trips/${tripId}/nodes/${nodeId}/tts`, null, { params: { voice } }),
  generateTTSAll: (tripId: number, voice: string = 'xiaoxiao') =>
    api.post(`/memory/trips/${tripId}/tts-all`, null, { params: { voice } }),
  bgmList: () => api.get('/memory/bgm-list'),
  updateNode: (tripId: number, nodeId: number, data: any) =>
    api.put(`/memory/trips/${tripId}/nodes/${nodeId}`, null, { params: data }),
  delete: (id: number) => api.delete(`/memory/trips/${id}`),
}

export default api
