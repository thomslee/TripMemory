<template>
  <div class="tm-page baidu-sync">
    <div class="sync-header">
      <button class="back-btn" @click="router.back()">
        <van-icon name="arrow-left" />
      </button>
      <h1 class="page-title">百度网盘同步</h1>
    </div>

    <!-- 步骤1：授权 -->
    <div v-if="step === 1" class="step-card tm-card">
      <div class="step-number">1</div>
      <h3>授权百度网盘</h3>
      <p class="step-desc">点击下方按钮，在浏览器中授权访问你的百度网盘照片。</p>
      <button class="tm-btn tm-btn-primary" @click="onGetAuthUrl">
        <van-icon name="lock" />
        去授权
      </button>
      <div v-if="authUrl" class="auth-url-box">
        <p>如果按钮没有跳转，请复制以下链接在浏览器中打开：</p>
        <div class="url-text">{{ authUrl }}</div>
      </div>
    </div>

    <!-- 步骤2：输入授权码 -->
    <div v-if="step === 2" class="step-card tm-card">
      <div class="step-number">2</div>
      <h3>输入授权码</h3>
      <p class="step-desc">在浏览器中完成授权后，页面会显示一个授权码，请复制粘贴到下方。</p>
      <van-field
        v-model="authCode"
        label="授权码"
        placeholder="请输入授权码"
        clearable
      />
      <button
        class="tm-btn tm-btn-primary"
        :disabled="!authCode || authorizing"
        @click="onAuthCallback"
      >
        {{ authorizing ? '验证中…' : '确认授权' }}
      </button>
    </div>

    <!-- 步骤3：选择文件夹 -->
    <div v-if="step === 3" class="step-card tm-card">
      <div class="step-number">3</div>
      <h3>选择照片文件夹</h3>
      <div class="user-info-bar">
        <van-icon name="user-o" />
        <span>{{ userInfo?.baidu_name || '已授权' }}</span>
      </div>
      <div class="path-nav">
        <button class="path-btn" @click="goUp" :disabled="currentDir === '/'">
          <van-icon name="arrow-up" /> 上级
        </button>
        <span class="current-path">{{ currentDir }}</span>
      </div>
      <div v-if="loadingFolders" class="loading-tip">加载中…</div>
      <div v-else class="folder-list">
        <div
          v-for="folder in folders"
          :key="folder.fs_id"
          class="folder-item"
          @click="enterFolder(folder.path)"
        >
          <van-icon name="folder" size="24" color="#e8a87c" />
          <span class="folder-name">{{ folder.name }}</span>
          <van-icon name="arrow" />
        </div>
        <div v-if="folders.length === 0" class="empty-tip">此目录下没有文件夹</div>
      </div>
      <button
        class="tm-btn tm-btn-primary"
        :disabled="currentDir === '/'"
        @click="onSelectFolder"
      >
        选择此文件夹
      </button>
    </div>

    <!-- 步骤4：预览并同步 -->
    <div v-if="step === 4" class="step-card tm-card">
      <div class="step-number">4</div>
      <h3>预览并同步照片</h3>
      <div class="selected-folder">
        <van-icon name="folder-o" />
        <span>{{ selectedFolder }}</span>
      </div>
      <div v-if="loadingPhotos" class="loading-tip">正在扫描照片…</div>
      <div v-else>
        <p class="photo-count">共发现 <strong>{{ photoCount }}</strong> 张照片</p>
        <div class="photo-preview">
          <div v-for="photo in previewPhotos" :key="photo.fs_id" class="preview-item">
            <div class="preview-thumb">
              <van-icon name="photo-o" size="20" />
            </div>
            <span class="preview-name">{{ photo.filename }}</span>
            <span class="preview-date">{{ formatDate(photo.date_taken) }}</span>
          </div>
        </div>
        <button
          class="tm-btn tm-btn-primary"
          :disabled="syncing || photoCount === 0"
          @click="onSyncPhotos"
        >
          {{ syncing ? '同步中…' : `同步到行程（${photoCount}张）` }}
        </button>
      </div>
    </div>

    <!-- 同步结果 -->
    <div v-if="step === 5" class="step-card tm-card result-card">
      <div class="result-icon success">
        <van-icon name="checked" size="40" />
      </div>
      <h3>同步完成</h3>
      <p>{{ syncResult?.message }}</p>
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-num">{{ syncResult?.synced || 0 }}</span>
          <span class="stat-label">新增</span>
        </div>
        <div class="stat-item">
          <span class="stat-num">{{ syncResult?.skipped || 0 }}</span>
          <span class="stat-label">已存在</span>
        </div>
      </div>
      <button class="tm-btn tm-btn-primary" @click="router.push(`/memory/${tripId}`)">
        查看记忆行程
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { baidunetApi } from '../api'

const route = useRoute()
const router = useRouter()

const tripId = ref(Number(route.params.tripId) || 0)
const step = ref(1)
const authUrl = ref('')
const authCode = ref('')
const authorizing = ref(false)
const accessToken = ref('')
const userInfo = ref<any>(null)
const currentDir = ref('/')
const folders = ref<any[]>([])
const loadingFolders = ref(false)
const selectedFolder = ref('')
const loadingPhotos = ref(false)
const photoCount = ref(0)
const previewPhotos = ref<any[]>([])
const syncing = ref(false)
const syncResult = ref<any>(null)

async function onGetAuthUrl() {
  try {
    const res: any = await baidunetApi.getAuthUrl()
    authUrl.value = res.auth_url
    window.open(res.auth_url, '_blank')
    step.value = 2
  } catch (e) {
    showToast('获取授权链接失败')
  }
}

async function onAuthCallback() {
  if (!authCode.value) return
  authorizing.value = true
  try {
    const res: any = await baidunetApi.authCallback(authCode.value)
    accessToken.value = res.access_token
    // 获取用户信息
    const info: any = await baidunetApi.getUserInfo(res.access_token)
    userInfo.value = info
    step.value = 3
    await loadFolders('/')
  } catch (e: any) {
    showToast(e.response?.data?.detail || '授权失败')
  } finally {
    authorizing.value = false
  }
}

async function loadFolders(dir: string) {
  loadingFolders.value = true
  try {
    const res: any = await baidunetApi.listFolders(accessToken.value, dir)
    folders.value = res.folders
    currentDir.value = dir
  } catch (e) {
    showToast('加载文件夹失败')
  } finally {
    loadingFolders.value = false
  }
}

function enterFolder(path: string) {
  loadFolders(path)
}

function goUp() {
  if (currentDir.value === '/') return
  const parts = currentDir.value.split('/').filter(Boolean)
  parts.pop()
  const parent = '/' + parts.join('/')
  loadFolders(parent || '/')
}

async function onSelectFolder() {
  selectedFolder.value = currentDir.value
  step.value = 4
  await loadPhotos()
}

async function loadPhotos() {
  loadingPhotos.value = true
  try {
    const res: any = await baidunetApi.listPhotos(accessToken.value, selectedFolder.value)
    photoCount.value = res.total
    previewPhotos.value = res.photos.slice(0, 10)
  } catch (e) {
    showToast('加载照片失败')
  } finally {
    loadingPhotos.value = false
  }
}

async function onSyncPhotos() {
  if (!tripId.value) {
    showToast('缺少行程ID')
    return
  }
  syncing.value = true
  try {
    const res: any = await baidunetApi.syncPhotos(tripId.value, accessToken.value, selectedFolder.value)
    syncResult.value = res
    step.value = 5
    showToast('同步完成')
  } catch (e: any) {
    showToast(e.response?.data?.detail || '同步失败')
  } finally {
    syncing.value = false
  }
}

function formatDate(dateStr: any): string {
  if (!dateStr) return '未知时间'
  if (typeof dateStr === 'number') {
    return new Date(dateStr * 1000).toLocaleString('zh-CN')
  }
  return String(dateStr)
}
</script>

<style scoped>
.baidu-sync {
  padding-bottom: 40px;
}

.sync-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.back-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--tm-card);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.step-card {
  position: relative;
  padding-top: 24px;
}

.step-number {
  position: absolute;
  top: -12px;
  left: 16px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--tm-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.step-card h3 {
  font-size: 16px;
  margin: 0 0 8px;
}

.step-desc {
  font-size: 13px;
  color: var(--tm-ink-2);
  margin: 0 0 16px;
  line-height: 1.6;
}

.step-card .tm-btn {
  width: 100%;
  margin-top: 12px;
  padding: 12px;
}

.auth-url-box {
  margin-top: 16px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.auth-url-box p {
  font-size: 12px;
  color: var(--tm-ink-2);
  margin: 0 0 8px;
}

.url-text {
  font-size: 11px;
  color: var(--tm-ink-3);
  word-break: break-all;
  background: #fff;
  padding: 8px;
  border-radius: 4px;
}

.user-info-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--tm-primary-light);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--tm-primary);
}

.path-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.path-btn {
  padding: 6px 10px;
  border: 1px solid var(--tm-line);
  background: #fff;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.path-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.current-path {
  font-size: 13px;
  color: var(--tm-ink-2);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.folder-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--tm-line);
  cursor: pointer;
}

.folder-item:active {
  background: #f9fafb;
}

.folder-name {
  flex: 1;
  font-size: 14px;
}

.empty-tip {
  text-align: center;
  padding: 30px;
  color: var(--tm-ink-3);
  font-size: 13px;
}

.loading-tip {
  text-align: center;
  padding: 20px;
  color: var(--tm-ink-3);
}

.selected-folder {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #f9fafb;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--tm-ink-2);
}

.photo-count {
  font-size: 14px;
  margin: 0 0 12px;
}

.photo-count strong {
  color: var(--tm-primary);
  font-size: 18px;
}

.photo-preview {
  max-height: 250px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-bottom: 1px solid var(--tm-line);
}

.preview-thumb {
  width: 40px;
  height: 40px;
  background: #f0f0f0;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
  flex-shrink: 0;
}

.preview-name {
  flex: 1;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-date {
  font-size: 11px;
  color: var(--tm-ink-3);
  flex-shrink: 0;
}

.result-card {
  text-align: center;
}

.result-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.result-icon.success {
  background: var(--tm-primary-light);
  color: var(--tm-primary);
}

.result-card h3 {
  font-size: 18px;
  margin: 0 0 8px;
}

.result-card p {
  font-size: 13px;
  color: var(--tm-ink-2);
  margin: 0 0 20px;
}

.result-stats {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
}

.stat-num {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--tm-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--tm-ink-3);
}
</style>
