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
}

// 记忆行程API
export const memoryApi = {
  list: () => api.get('/memory/trips'),
  detail: (id: number) => api.get(`/memory/trips/${id}`),
  syncFromTripCanvas: (tripcanvasTripId: number) =>
    api.post(`/memory/sync-from-tripcanvas/${tripcanvasTripId}`),
  matchPhotos: (id: number) => api.post(`/memory/trips/${id}/match-photos`),
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

// 百度网盘API
export const baidunetApi = {
  getAuthUrl: () => api.get('/baidunet/auth-url'),
  authCallback: (code: string) => api.post('/baidunet/callback', null, { params: { code } }),
  getUserInfo: (accessToken: string) => api.get('/baidunet/user-info', { params: { access_token: accessToken } }),
  listFolders: (accessToken: string, dir: string = '/') =>
    api.get('/baidunet/folders', { params: { access_token: accessToken, dir } }),
  listPhotos: (accessToken: string, folderPath: string) =>
    api.get('/baidunet/photos', { params: { access_token: accessToken, folder_path: folderPath } }),
  syncPhotos: (tripId: number, accessToken: string, folderPath: string) =>
    api.post(`/baidunet/sync/${tripId}`, null, { params: { access_token: accessToken, folder_path: folderPath } }),
}

export default api
