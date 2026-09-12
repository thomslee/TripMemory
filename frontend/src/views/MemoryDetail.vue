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
        <button class="tm-btn tm-btn-outline action-btn" :disabled="matching" @click="onMatchPhotos">
          <van-icon name="photo-o" />
          {{ matching ? '匹配中…' : '匹配照片' }}
        </button>
        <button class="tm-btn tm-btn-outline action-btn" :disabled="generating" @click="onGenerateAllArticles">
          <van-icon name="edit" />
          {{ generating ? '生成中…' : 'AI生成游记' }}
        </button>
        <button class="tm-btn tm-btn-outline action-btn" @click="router.push(`/baidu-sync/${trip.id}`)">
          <van-icon name="cloud-o" />
          网盘同步
        </button>
      </div>

      <!-- 配音批量生成 -->
      <div class="tts-row">
        <button class="tm-btn tm-btn-outline action-btn" :disabled="ttsGenerating" @click="onGenerateAllTTS">
          <van-icon name="volume-o" />
          {{ ttsGenerating ? '生成配音中…' : '生成全部配音' }}
        </button>
        <span class="tts-hint">自动朗读每篇游记，供动态展示页播放</span>
      </div>

      <!-- 未匹配照片 -->
      <div v-if="trip.unmatched_photos.length > 0" class="unmatched-section">
        <h3 class="section-title">未匹配照片 ({{ trip.unmatched_photos.length }})</h3>
        <div class="photo-grid">
          <div v-for="photo in trip.unmatched_photos" :key="photo.id" class="photo-item">
            <div class="photo-thumb">
              <van-icon name="photo-o" size="24" />
            </div>
            <span class="photo-name">{{ photo.filename }}</span>
          </div>
        </div>
      </div>

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

          <!-- 照片 -->
          <div v-if="node.photos.length > 0" class="node-photos">
            <div class="photo-row">
              <div v-for="photo in node.photos.slice(0, 4)" :key="photo.id" class="photo-thumb small">
                <van-icon name="photo-o" size="20" />
              </div>
              <div v-if="node.photos.length > 4" class="photo-more">
                +{{ node.photos.length - 4 }}
              </div>
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
    showToast(`匹配完成：${res.matched}张匹配，${res.unmatched}张未匹配`)
    await loadTrip()
  } catch (e) {
    showToast('匹配失败')
  } finally {
    matching.value = false
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

.photo-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.photo-more {
  width: 56px;
  height: 56px;
  background: #f0f0f0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--tm-ink-2);
}

.node-article {
  background: var(--tm-primary-light);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 10px;
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
