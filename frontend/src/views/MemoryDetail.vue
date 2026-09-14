<template>
  <div class="tm-page memory-detail">
    <div class="detail-header">
      <button class="back-btn" @click="router.back()">
        <van-icon name="arrow-left" />
      </button>
      <h1 class="detail-title">{{ trip?.title || '加载中…' }}</h1>
    </div>

    <div v-if="loading" class="loading-tip">加载中…</div>

    <template v-else-if="trip">
      <!-- 行程概览 -->
      <div class="overview-card tm-card">
        <div class="overview-row">
          <div class="overview-item">
            <span class="overview-label">目的地</span>
            <span class="overview-value">{{ trip.dest_city || '未设置' }}</span>
          </div>
          <div class="overview-item">
            <span class="overview-label">天数</span>
            <span class="overview-value">{{ trip.total_days }}天</span>
          </div>
          <div class="overview-item">
            <span class="overview-label">照片</span>
            <span class="overview-value">{{ trip.nodes.reduce((s: number, n: any) => s + n.photos.length, 0) + trip.unmatched_photos.length }}张</span>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="action-row">
        <button class="tm-btn tm-btn-primary action-btn" @click="router.push(`/memory/${trip.id}/showcase`)">
          <van-icon name="play-circle-o" />
          动态展示
        </button>
        <button class="tm-btn tm-btn-outline action-btn" @click="libraryShow = true">
          <van-icon name="photo-o" />
          照片库
        </button>
        <button class="tm-btn tm-btn-outline action-btn" :disabled="generating" @click="onGenerateAllArticles">
          <van-icon name="edit" />
          {{ generating ? '生成中…' : 'AI生成游记' }}
        </button>
        <button class="tm-btn tm-btn-outline action-btn" :class="{ 'tm-btn-active': showUploader }" @click="showUploader = !showUploader">
          <van-icon name="plus" />
          上传照片
        </button>
      </div>

      <!-- 照片上传面板（本地目录 / 手机图库精选） -->
      <div v-if="showUploader" class="uploader-card tm-card">
        <div class="uploader-title">上传精选照片</div>
        <div class="uploader-desc">支持电脑本地目录或手机图库多选；自动提取拍摄时间匹配到行程节点，可压缩存储</div>
        <van-uploader
          v-model="uploadFiles"
          multiple
          :max-count="50"
          accept="image/*"
          :after-read="onAfterRead"
          :before-read="beforeRead"
          :disabled="uploading"
        >
          <div class="uploader-trigger">
            <van-icon name="photograph" size="22" />
            <span>{{ uploading ? '上传中…' : '选择照片' }}</span>
          </div>
        </van-uploader>
      </div>

      <!-- 配音批量生成 -->
      <div class="tts-row">
        <button class="tm-btn tm-btn-outline action-btn" :disabled="ttsGenerating" @click="onGenerateAllTTS">
          <van-icon name="volume-o" />
          {{ ttsGenerating ? '生成配音中…' : '生成全部配音' }}
        </button>
        <span class="tts-hint">自动朗读每篇游记，供动态展示页播放</span>
      </div>

      <!-- 照片库（全部照片集中管理） -->
      <van-popup v-model:show="libraryShow" position="right" class="library-popup">
        <div class="library-header">
          <button class="back-btn" @click="libraryShow = false">
            <van-icon name="arrow-left" />
          </button>
          <h3 class="library-title">照片库 ({{ allPhotos.length }})</h3>
          <button class="lib-match-btn" :disabled="matching" @click="onMatchPhotos">
            {{ matching ? '匹配中…' : '自动匹配' }}
          </button>
        </div>
        <div class="library-hint">点击照片放大查看，可调整关联节点或删除</div>
        <div class="library-grid">
          <div v-for="photo in allPhotos" :key="photo.id" class="library-item" @click="openViewer(photo)">
            <van-image :src="photo.display_url" fit="cover" class="lib-thumb" />
            <span class="lib-node-name" :class="{ unassigned: !photo.node_name }">
              {{ photo.node_name || '未关联' }}
            </span>
          </div>
        </div>
      </van-popup>

      <!-- 照片放大查看 -->
      <van-popup v-model:show="viewerShow" class="viewer-popup">
        <div class="viewer-body" @click="viewerShow = false">
          <van-image :src="viewerPhoto?.display_url" fit="contain" class="viewer-img" />
        </div>
        <div class="viewer-footer">
          <div class="viewer-node">当前关联：{{ viewerPhoto?.node_name || '未关联' }}</div>
          <div class="viewer-actions">
            <button class="tm-btn tm-btn-outline action-btn" @click="onViewerAssign">
              <van-icon name="exchange" />
              调整节点
            </button>
            <button class="tm-btn tm-btn-danger action-btn" @click="onDeletePhoto(viewerPhoto)">
              <van-icon name="delete-o" />
              删除照片
            </button>
          </div>
        </div>
      </van-popup>

      <!-- 删除照片确认 -->
      <van-dialog
        v-model:show="deleteDialog.show"
        title="删除照片"
        :show-cancel-button="true"
        confirm-button-color="#e54d42"
        @confirm="onDeleteConfirm"
        @cancel="deleteDialog.show = false"
      >
        <div class="delete-dialog-msg">
          确定删除「{{ deleteDialog.photo?.filename }}」吗？<br />删除后不可恢复。
        </div>
      </van-dialog>

      <!-- 手动关联节点选择 -->
      <van-action-sheet v-model:show="assignSheet.show" :actions="assignActions" cancel-text="取消关联" @select="onAssignSelect" @cancel="onAssignCancel" />

      <!-- 按天分组的节点 -->
      <div v-for="(dayNodes, dayNo) in groupedNodes" :key="dayNo" class="day-section">
        <div class="day-header">
          <span class="day-badge">第{{ dayNo }}天</span>
          <span class="day-city">{{ dayNodes[0]?.city || '' }}</span>
        </div>

        <div v-for="node in dayNodes" :key="node.id" class="node-card tm-card">
          <div class="node-header">
            <span class="node-type tm-tag">{{ typeNames[node.node_type] || node.node_type }}</span>
            <span class="node-time">{{ node.start_time || '' }}</span>
          </div>
          <h3 class="node-name">{{ node.name }}</h3>
          <div v-if="node.weather" class="node-weather">
            <van-icon name="weather-o" /> {{ node.weather }} {{ node.temperature || '' }}
          </div>

          <!-- 照片：点击可手动调整归属 -->
          <div v-if="node.photos.length > 0" class="node-photos">
            <div class="node-photos-hint">点击照片可调整归属</div>
            <div class="photo-row">
              <div v-for="photo in node.photos" :key="photo.id" class="photo-thumb small" @click="openAssign(photo)">
                <van-image :src="photo.display_url" fit="cover" width="100%" height="100%" />
              </div>
            </div>
          </div>

          <!-- 我的感想：文字/语音输入，AI生成游记时融入 -->
          <div class="node-note">
            <div class="node-note-header">
              <span class="node-note-title">我的感想</span>
              <button v-if="speechSupported" class="link-btn" :class="{ recording: node.recording }" @click="startVoiceNote(node)">
                {{ node.recording ? '● 停止' : '语音输入' }}
              </button>
            </div>
            <textarea
              v-model="node.noteDraft"
              class="node-note-input"
              rows="2"
              maxlength="500"
              placeholder="说说这里的风景、心情、小故事……AI 会把它融进游记"
            ></textarea>
            <div class="node-note-actions">
              <button class="link-btn" @click="saveNote(node)">保存感想</button>
              <span v-if="node.noteSaved" class="note-saved">已保存</span>
              <span v-if="node.recording" class="note-listening">聆听中…</span>
            </div>
          </div>

          <!-- 游记 -->
          <div v-if="node.article" class="node-article">
            <p>{{ node.article }}</p>
          </div>
          <div v-else class="node-article-empty">
            <button class="link-btn" @click="onGenerateArticle(node)">AI生成游记</button>
          </div>

          <!-- 音频 -->
          <div v-if="node.audio_url" class="node-audio">
            <van-icon name="volume-o" /> 游记配音
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { memoryApi } from '../api'

const route = useRoute()
const router = useRouter()

const trip = ref<any>(null)
const loading = ref(true)
const matching = ref(false)
const generating = ref(false)
const ttsGenerating = ref(false)
const showUploader = ref(false)
const uploadFiles = ref<any[]>([])
const uploading = ref(false)
const assignSheet = ref<{ show: boolean; photo: any }>({ show: false, photo: null })
const libraryShow = ref(false)
const viewerShow = ref(false)
const viewerPhoto = ref<any>(null)
const deleteDialog = ref<{ show: boolean; photo: any }>({ show: false, photo: null })

const typeNames: Record<string, string> = {
  hotel: '酒店',
  attraction: '景点',
  restaurant: '餐厅',
  station: '交通',
}

const groupedNodes = computed(() => {
  if (!trip.value?.nodes) return {}
  const groups: Record<string, any[]> = {}
  for (const node of trip.value.nodes) {
    const key = String(node.day_no)
    if (!groups[key]) groups[key] = []
    groups[key].push(node)
  }
  return groups
})

async function loadTrip() {
  loading.value = true
  try {
    const res: any = await memoryApi.detail(Number(route.params.id))
    res.nodes.forEach((n: any) => (n.noteDraft = n.note || ''))
    trip.value = res
  } catch (e) {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

async function onMatchPhotos() {
  matching.value = true
  try {
    const res: any = await memoryApi.matchPhotos(Number(route.params.id))
    if (res.total === 0) {
      showToast('暂无可匹配的照片，请先上传照片')
    } else {
      showToast(`匹配完成：${res.matched}张匹配，${res.unmatched}张未匹配`)
    }
    await loadTrip()
  } catch (e) {
    showToast('匹配失败')
  } finally {
    matching.value = false
  }
}

// ---- 照片上传 ----
function beforeRead(file: File | File[]): boolean {
  const files = Array.isArray(file) ? file : [file]
  for (const f of files) {
    // 图片类型交给后端识别（兼容手机 HEIC 等格式），前端只限制大小
    if (f.size > 20 * 1024 * 1024) {
      showToast('单张照片不能超过 20MB')
      return false
    }
  }
  return true
}

async function onAfterRead(file: any) {
  const files: File[] = (Array.isArray(file) ? file : [file]).map((f: any) => f.file)
  if (!files.length) return
  uploading.value = true
  // 分批上传（每批5张），避免单请求体过大被 nginx 拦截（413）
  const BATCH = 5
  let saved = 0
  let failed = 0
  let matched = 0
  const errors: string[] = []
  try {
    for (let i = 0; i < files.length; i += BATCH) {
      const batch = files.slice(i, i + BATCH)
      const res: any = await memoryApi.uploadPhotos(Number(route.params.id), batch)
      saved += res.saved || 0
      failed += res.failed || 0
      matched += (res.match && res.match.matched) || 0
      if (res.errors?.length) errors.push(...res.errors.map((e: any) => e.reason))
    }
    let msg = `共${files.length}张，成功上传${saved}张，自动匹配${matched}张`
    if (failed > 0) msg += `；${failed}张失败${errors.length ? '：' + errors[0] : ''}`
    showToast(msg)
    uploadFiles.value = []
    await loadTrip()
  } catch (e) {
    showToast('上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// ---- 照片库 ----
const allPhotos = computed(() => {
  if (!trip.value) return []
  const fromNodes: any[] = []
  for (const n of trip.value.nodes || []) {
    for (const p of n.photos || []) {
      fromNodes.push({ ...p, node_name: n.name })
    }
  }
  const fromUnmatched: any[] = (trip.value.unmatched_photos || []).map((p: any) => ({
    ...p,
    node_name: '',
  }))
  return [...fromNodes, ...fromUnmatched]
})

function openViewer(photo: any) {
  viewerPhoto.value = photo
  viewerShow.value = true
}

function onViewerAssign() {
  viewerShow.value = false
  openAssign(viewerPhoto.value)
}

function onDeletePhoto(photo: any) {
  if (!photo) return
  deleteDialog.value = { show: true, photo }
}

async function onDeleteConfirm() {
  const photo = deleteDialog.value.photo
  deleteDialog.value.show = false
  if (!photo) return
  viewerShow.value = false
  try {
    await memoryApi.deletePhoto(Number(route.params.id), photo.id)
    showToast('已删除')
    await loadTrip()
  } catch (e) {
    showToast('删除失败')
  }
}

// ---- 手动调整照片归属（节点照片与未匹配照片均可） ----
const assignActions = computed(() => {
  if (!trip.value?.nodes) return []
  const current = assignSheet.value.photo?.node_id
  return trip.value.nodes.map((n: any) => ({
    name: `第${n.day_no}天 · ${n.name}${n.id === current ? '（当前）' : ''}`,
    value: n.id,
  }))
})

function openAssign(photo: any) {
  assignSheet.value = { show: true, photo }
}

async function onAssignSelect(action: any) {
  assignSheet.value.show = false
  const photo = assignSheet.value.photo
  if (!photo) return
  if (action.value === photo.node_id) {
    // 选择当前节点，无变化
    return
  }
  try {
    await memoryApi.assignPhoto(Number(route.params.id), photo.id, action.value)
    showToast('已关联到节点')
    await loadTrip()
  } catch (e) {
    showToast('关联失败')
  }
}

async function onAssignCancel() {
  assignSheet.value.show = false
  const photo = assignSheet.value.photo
  if (!photo) return
  try {
    await memoryApi.assignPhoto(Number(route.params.id), photo.id, 0)
    showToast('已取消关联')
    await loadTrip()
  } catch (e) {
    showToast('操作失败')
  }
}

async function onGenerateArticle(node: any) {
  try {
    const res: any = await memoryApi.generateArticle(Number(route.params.id), node.id)
    node.article = res.article
    showToast('生成成功')
  } catch (e) {
    showToast('生成失败')
  }
}

// ---- 我的感想：保存 + 语音输入 ----
const speechSupported =
  typeof window !== 'undefined' && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)
let voiceRecognition: any = null

async function saveNote(node: any) {
  try {
    await memoryApi.updateNode(Number(route.params.id), node.id, { note: node.noteDraft || '' })
    node.note = node.noteDraft || ''
    node.noteSaved = true
    setTimeout(() => (node.noteSaved = false), 2000)
    showToast('感想已保存')
  } catch (e) {
    showToast('保存失败')
  }
}

function startVoiceNote(node: any) {
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SR) {
    showToast('当前浏览器不支持语音输入，请改用文字输入')
    return
  }
  if (!voiceRecognition) {
    voiceRecognition = new SR()
    voiceRecognition.lang = 'zh-CN'
    voiceRecognition.continuous = true
    voiceRecognition.interimResults = true
    voiceRecognition.onresult = (e: any) => {
      let text = ''
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript
      node.noteDraft = text
    }
    voiceRecognition.onend = () => {
      node.recording = false
    }
    voiceRecognition.onerror = () => {
      node.recording = false
      showToast('语音识别失败，请重试')
    }
  }
  if (node.recording) {
    voiceRecognition.stop()
    node.recording = false
  } else {
    node.recording = true
    node.noteDraft = ''
    try {
      voiceRecognition.start()
    } catch (e) {
      node.recording = false
    }
  }
}

async function onGenerateAllArticles() {
  if (!trip.value?.nodes) return
  generating.value = true
  let count = 0
  for (const node of trip.value.nodes) {
    if (node.node_type === 'attraction' && !node.article) {
      try {
        const res: any = await memoryApi.generateArticle(Number(route.params.id), node.id)
        node.article = res.article
        count++
      } catch (e) {
        // 继续下一个
      }
    }
  }
  generating.value = false
  showToast(`已生成${count}篇游记`)
}

async function onGenerateAllTTS() {
  if (!trip.value?.nodes) return
  ttsGenerating.value = true
  try {
    const res: any = await memoryApi.generateTTSAll(Number(route.params.id))
    showToast(res.message || '配音生成完成')
    await loadTrip()
  } catch (e) {
    showToast('配音生成失败')
  } finally {
    ttsGenerating.value = false
  }
}

onMounted(loadTrip)
</script>

<style scoped>
.memory-detail {
  padding-bottom: 40px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
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

.detail-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.loading-tip {
  text-align: center;
  padding: 40px;
  color: var(--tm-ink-3);
}

.overview-row {
  display: flex;
  justify-content: space-around;
}

.overview-item {
  text-align: center;
}

.overview-label {
  display: block;
  font-size: 12px;
  color: var(--tm-ink-3);
  margin-bottom: 4px;
}

.overview-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--tm-ink);
}

.action-row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tts-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.tts-hint {
  font-size: 12px;
  color: var(--tm-ink-3);
}

.action-btn {
  flex: 1;
  padding: 10px;
  font-size: 13px;
}

.tm-btn-active {
  border-color: var(--tm-primary);
  color: var(--tm-primary);
  background: var(--tm-primary-light);
}

.uploader-card {
  margin-bottom: 16px;
  padding: 14px;
}

.uploader-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}

.uploader-desc {
  font-size: 12px;
  color: var(--tm-ink-3);
  margin-bottom: 12px;
}

.uploader-trigger {
  width: 96px;
  height: 96px;
  border: 1px dashed #c8c9cc;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: var(--tm-ink-3);
  font-size: 12px;
}

.section-hint {
  font-size: 11px;
  color: var(--tm-ink-3);
  font-weight: 400;
}

.unmatched-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 10px;
  color: var(--tm-ink);
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.photo-item {
  text-align: center;
}

.photo-thumb {
  width: 100%;
  aspect-ratio: 1;
  background: #f0f0f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
  margin-bottom: 4px;
}

.photo-thumb.small {
  width: 56px;
  height: 56px;
}

.photo-name {
  font-size: 10px;
  color: var(--tm-ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

/* ---- 照片库 ---- */
.library-popup {
  width: 100%;
  height: 100%;
  background: var(--tm-bg);
  display: flex;
  flex-direction: column;
}

.library-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--tm-line);
  flex-shrink: 0;
}

.library-title {
  flex: 1;
  margin: 0;
  font-size: 16px;
  color: var(--tm-ink);
}

.lib-match-btn {
  border: none;
  background: var(--tm-primary);
  color: #fff;
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 14px;
}

.lib-match-btn:disabled {
  opacity: 0.6;
}

.library-hint {
  padding: 8px 16px 0;
  font-size: 11px;
  color: var(--tm-ink-3);
  flex-shrink: 0;
}

.library-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 12px 16px;
}

.library-item {
  text-align: center;
}

.lib-thumb {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8px;
  background: #f0f0f0;
}

.lib-node-name {
  display: block;
  margin-top: 4px;
  font-size: 10px;
  color: var(--tm-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lib-node-name.unassigned {
  color: var(--tm-ink-3);
}

/* ---- 照片放大查看 ---- */
.viewer-popup {
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  flex-direction: column;
}

.viewer-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.viewer-img {
  width: 100%;
  height: 100%;
}

.viewer-footer {
  padding: 14px 16px calc(14px + env(safe-area-inset-bottom));
  background: rgba(0, 0, 0, 0.7);
  flex-shrink: 0;
}

.viewer-node {
  color: #fff;
  font-size: 13px;
  margin-bottom: 10px;
  text-align: center;
}

.viewer-actions {
  display: flex;
  gap: 10px;
}

.delete-dialog-msg {
  padding: 8px 16px 20px;
  font-size: 14px;
  color: var(--tm-ink);
  line-height: 1.6;
  text-align: center;
}

.tm-btn-danger {
  background: #fff;
  color: #e54d42;
  border: 1px solid #e54d42;
}

.day-section {
  margin-bottom: 20px;
}

.day-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.day-badge {
  background: var(--tm-primary);
  color: #fff;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.day-city {
  font-size: 13px;
  color: var(--tm-ink-2);
}

.node-card {
  margin-bottom: 10px;
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.node-time {
  font-size: 12px;
  color: var(--tm-ink-3);
}

.node-name {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--tm-ink);
}

.node-weather {
  font-size: 12px;
  color: var(--tm-ink-2);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.node-photos {
  margin-bottom: 10px;
}

.node-photos-hint {
  font-size: 11px;
  color: var(--tm-ink-2);
  margin-bottom: 4px;
}

.photo-row {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.node-note {
  margin-bottom: 10px;
  background: #f7f7f8;
  border-radius: 8px;
  padding: 8px 10px;
}

.node-note-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.node-note-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--tm-ink-2);
}

.node-note-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #ebedf0;
  border-radius: 6px;
  padding: 8px;
  font-size: 13px;
  font-family: inherit;
  line-height: 1.5;
  resize: vertical;
  background: #fff;
  color: var(--tm-ink);
}

.node-note-input:focus {
  outline: none;
  border-color: var(--tm-primary);
}

.node-note-actions {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.note-saved {
  font-size: 12px;
  color: var(--tm-primary);
}

.note-listening {
  font-size: 12px;
  color: #e64340;
  animation: blink 1s infinite;
}

@keyframes blink {
  50% {
    opacity: 0.3;
  }
}

.link-btn.recording {
  color: #e64340;
}

.node-article {
  background: var(--tm-primary-light);
  border-radius: 8px;
  padding: 10px 12px;  margin-top: 10px;
}

.node-article p {
  font-size: 13px;
  line-height: 1.7;
  color: var(--tm-ink);
  margin: 0;
}

.node-article-empty {
  margin-top: 8px;
}

.link-btn {
  background: none;
  border: none;
  color: var(--tm-primary);
  font-size: 13px;
  cursor: pointer;
  padding: 0;
}

.node-audio {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 8px;
  font-size: 13px;
  color: var(--tm-ink-2);
}
</style>
