<template>
  <div class="showcase" :class="{ 'bgm-on': bgmPlaying }">
    <!-- 封面 Hero -->
    <header class="hero" :style="heroStyle">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div class="hero-tag" v-if="trip?.dest_city">{{ trip.dest_city }}</div>
        <h1 class="hero-title">{{ trip?.title || '旅途记忆' }}</h1>
        <div class="hero-meta">
          <span v-if="dateRange">{{ dateRange }}</span>
          <span v-if="trip?.total_days">{{ trip.total_days }} 天</span>
          <span>{{ totalPhotos }} 张照片</span>
          <span>{{ nodeCount }} 个地点</span>
        </div>
        <button class="hero-play" @click="onPlayTrip">
          <van-icon :name="playingAll ? 'pause-circle-o' : 'play-circle-o'" size="22" />
          {{ playingAll ? '暂停连播' : '开始回忆之旅' }}
        </button>
      </div>
      <div class="hero-scroll-hint">
        <van-icon name="down" />
      </div>
    </header>

    <div v-if="loading" class="loading-state">
      <van-loading color="#f5c56b" vertical>正在翻开记忆…</van-loading>
    </div>

    <template v-else-if="trip">
      <main class="story">
        <!-- 每日章节 -->
        <section v-for="(dayNodes, dayNo) in groupedNodes" :key="dayNo" class="chapter" :data-day="dayNo">
          <div class="chapter-head reveal">
            <div class="chapter-day">DAY {{ dayNo }}</div>
            <div class="chapter-city">{{ dayNodes[0]?.city || '' }}</div>
            <div class="chapter-line"></div>
          </div>

          <!-- 节点 -->
          <article
            v-for="(node, idx) in dayNodes"
            :key="node.id"
            class="node-card reveal"
            :data-node-id="node.id"
            :style="{ '--delay': idx * 60 + 'ms' }"
          >
            <!-- 照片墙 -->
            <div v-if="node.photos.length" class="photo-wall" :class="'wall-' + Math.min(node.photos.length, 3)">
              <div
                v-for="(p, pi) in node.photos"
                :key="p.id"
                class="photo-item"
                :class="{ cover: pi === 0 && node.photos.length > 1 }"
                @click="openLightbox(node.photos, pi)"
              >
                <img :src="p.display_url" :alt="p.filename" loading="lazy" @error="onImgError" />
              </div>
            </div>

            <div class="node-body">
              <div class="node-head">
                <span class="node-type" :class="node.node_type">{{ typeNames[node.node_type] || node.node_type }}</span>
                <span class="node-time">{{ node.start_time || '' }}</span>
                <span v-if="node.weather" class="node-weather">
                  <van-icon name="weather-o" /> {{ node.weather }}{{ node.temperature ? ' ' + node.temperature + '°' : '' }}
                </span>
              </div>
              <h2 class="node-name">{{ node.name }}</h2>
              <p v-if="node.article" class="node-article">{{ node.article }}</p>
              <div v-if="node.audio_url" class="node-audio">
                <button class="audio-btn" :class="{ playing: currentAudio === node.id }" @click="onPlayNode(node)">
                  <van-icon :name="currentAudio === node.id ? 'pause-circle-o' : 'play-circle-o'" size="26" />
                  <span>{{ currentAudio === node.id ? '暂停' : '聆听游记' }}</span>
                </button>
              </div>
            </div>
          </article>
        </section>

        <!-- 结尾 -->
        <footer class="story-end reveal">
          <div class="end-line"></div>
          <p class="end-text">旅途有终点，记忆没有。</p>
          <button class="back-btn" @click="router.push(`/memory/${trip.id}`)">
            <van-icon name="arrow-left" /> 返回行程详情
          </button>
        </footer>
      </main>

      <!-- 底部 BGM 控制条 -->
      <div class="bgm-bar">
        <button class="bgm-toggle" :class="{ on: bgmPlaying }" @click="toggleBgm">
          <van-icon :name="bgmPlaying ? 'music' : 'music-o'" size="20" />
          <span>{{ bgmPlaying ? '音乐播放中' : '打开背景音乐' }}</span>
        </button>
        <button v-if="bgmTracks.length > 1" class="bgm-switch" @click="cycleBgm">
          <van-icon name="exchange" size="16" /> {{ currentBgmName }}
        </button>
      </div>
    </template>

    <!-- 照片灯箱 -->
    <div v-if="lightbox.show" class="lightbox" @click="closeLightbox">
      <div class="lightbox-img-wrap" @click.stop>
        <img :src="lightbox.list[lightbox.index]?.display_url" />
        <div class="lightbox-nav">
          <button v-if="lightbox.index > 0" class="lb-btn" @click.stop="lightbox.index--">
            <van-icon name="arrow-left" size="22" />
          </button>
          <button v-if="lightbox.index < lightbox.list.length - 1" class="lb-btn" @click.stop="lightbox.index++">
            <van-icon name="arrow" size="22" />
          </button>
        </div>
        <button class="lb-close" @click.stop="closeLightbox">
          <van-icon name="cross" size="20" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from 'vant'
import { memoryApi } from '../api'

const route = useRoute()
const router = useRouter()

const trip = ref<any>(null)
const loading = ref(true)
const bgmTracks = ref<any[]>([])
const currentBgmIndex = ref(0)
const bgmPlaying = ref(false)
const bgmEl = ref<HTMLAudioElement | null>(null)

const narrationEl = ref<HTMLAudioElement | null>(null)
const currentAudio = ref<number | null>(null)
const playingAll = ref(false)
const allNodeQueue = ref<any[]>([])

const lightbox = ref<{ show: boolean; list: any[]; index: number }>({
  show: false,
  list: [],
  index: 0,
})

const typeNames: Record<string, string> = {
  hotel: '住宿',
  attraction: '景点',
  restaurant: '美食',
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

const totalPhotos = computed(() => {
  if (!trip.value?.nodes) return 0
  return trip.value.nodes.reduce((s: number, n: any) => s + (n.photos?.length || 0), 0)
})

const nodeCount = computed(() => trip.value?.nodes?.length || 0)

const dateRange = computed(() => {
  const nodes = trip.value?.nodes || []
  if (!nodes.length) return ''
  const times = nodes.map((n: any) => n.start_time).filter(Boolean)
  return times.length ? `${times[0]} 出发` : ''
})

const heroStyle = computed(() => {
  const cover = trip.value?.nodes?.find((n: any) => n.photos?.length)?.photos?.[0]
  const url = cover?.display_url
  return url ? { backgroundImage: `url(${url})` } : {}
})

const currentBgmName = computed(() => bgmTracks.value[currentBgmIndex.value]?.name || '')

/* ---------- 数据加载 ---------- */
async function load() {
  loading.value = true
  try {
    const res: any = await memoryApi.detail(Number(route.params.id))
    trip.value = res
    await loadBgm()
    // 连播队列：所有有配音的节点
    allNodeQueue.value = (res.nodes || []).filter((n: any) => n.audio_url)
  } catch (e) {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

async function loadBgm() {
  try {
    const res: any = await memoryApi.bgmList()
    bgmTracks.value = res.tracks || []
  } catch {
    bgmTracks.value = []
  }
}

/* ---------- 滚动淡入 ---------- */
let observer: IntersectionObserver | null = null

function setupReveal() {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add('in')
          observer?.unobserve(en.target)
        }
      })
    },
    { threshold: 0.12 },
  )
  document.querySelectorAll('.reveal').forEach((el) => observer?.observe(el))
}

/* ---------- 音频控制 ---------- */
function stopNarration() {
  if (narrationEl.value) {
    narrationEl.value.pause()
    narrationEl.value.currentTime = 0
  }
  currentAudio.value = null
}

function onPlayNode(node: any) {
  if (currentAudio.value === node.id && narrationEl.value && !narrationEl.value.paused) {
    stopNarration()
    return
  }
  stopNarration()
  const audio = new Audio(node.audio_url)
  audio.addEventListener('ended', () => {
    currentAudio.value = null
    if (playingAll.value) playNextInQueue()
  })
  audio.play().catch(() => showToast('播放失败，请检查配音文件'))
  narrationEl.value = audio
  currentAudio.value = node.id
}

function playNextInQueue() {
  const idx = allNodeQueue.value.findIndex((n) => n.id === currentAudio.value)
  const next = allNodeQueue.value[idx + 1]
  if (!next) {
    playingAll.value = false
    return
  }
  // 滚动到下一个节点
  const cards = document.querySelectorAll('.node-card')
  const target = Array.from(cards).find((el) => (el as HTMLElement).dataset?.nodeId === String(next.id))
  target?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  onPlayNode(next)
}

function onPlayTrip() {
  if (playingAll.value) {
    playingAll.value = false
    stopNarration()
    return
  }
  if (!allNodeQueue.value.length) {
    showToast('还没有游记配音，请先在详情页生成')
    return
  }
  playingAll.value = true
  onPlayNode(allNodeQueue.value[0])
}

/* ---------- BGM ---------- */
function playBgm() {
  if (!bgmTracks.value.length) {
    showToast('暂无背景音乐')
    return
  }
  const track = bgmTracks.value[currentBgmIndex.value]
  if (!bgmEl.value) {
    bgmEl.value = new Audio(track.url)
    bgmEl.value.loop = true
    bgmEl.value.volume = 0.35
    bgmEl.value.addEventListener('ended', () => {
      // 循环播放
    })
  } else if (bgmEl.value.src !== new URL(track.url, window.location.origin).href) {
    bgmEl.value.src = track.url
  }
  bgmEl.value.volume = 0.35
  bgmEl.value.play().catch(() => showToast('背景音乐播放失败'))
  bgmPlaying.value = true
}

function toggleBgm() {
  if (bgmPlaying.value) {
    bgmEl.value?.pause()
    bgmPlaying.value = false
  } else {
    playBgm()
  }
}

function cycleBgm() {
  if (!bgmTracks.value.length) return
  currentBgmIndex.value = (currentBgmIndex.value + 1) % bgmTracks.value.length
  if (bgmPlaying.value) {
    // 直接切换曲目
    const track = bgmTracks.value[currentBgmIndex.value]
    if (bgmEl.value) {
      bgmEl.value.src = track.url
      bgmEl.value.play().catch(() => {})
    }
  }
}

/* ---------- 照片灯箱 ---------- */
function openLightbox(list: any[], index: number) {
  lightbox.value = { show: true, list, index }
}

function closeLightbox() {
  lightbox.value.show = false
}

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  img.style.visibility = 'hidden'
}

onMounted(() => {
  load().then(() => {
    // 等待DOM渲染
    requestAnimationFrame(setupReveal)
  })
})

onBeforeUnmount(() => {
  observer?.disconnect()
  stopNarration()
  bgmEl.value?.pause()
})
</script>

<style scoped>
.showcase {
  min-height: 100vh;
  background: linear-gradient(180deg, #101a1f 0%, #0d1518 45%, #0a1013 100%);
  color: #e8e2d5;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ---------- Hero ---------- */
.hero {
  position: relative;
  min-height: 62vh;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0 20px 56px;
  background-size: cover;
  background-position: center;
}
.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    180deg,
    rgba(13, 21, 24, 0.35) 0%,
    rgba(13, 21, 24, 0.55) 50%,
    #0d1518 100%
  );
}
.hero-content {
  position: relative;
  text-align: center;
  max-width: 520px;
  animation: fadeUp 0.9s ease both;
}
.hero-tag {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 4px;
  color: #f5c56b;
  border: 1px solid rgba(245, 197, 107, 0.5);
  border-radius: 999px;
  padding: 4px 16px;
  margin-bottom: 14px;
}
.hero-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 14px;
  letter-spacing: 2px;
  line-height: 1.3;
  color: #fbf7ec;
}
.hero-meta {
  display: flex;
  justify-content: center;
  gap: 16px;
  font-size: 12.5px;
  color: rgba(232, 226, 213, 0.75);
  margin-bottom: 22px;
  flex-wrap: wrap;
}
.hero-play {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(245, 197, 107, 0.15);
  border: 1px solid rgba(245, 197, 107, 0.6);
  color: #f5c56b;
  font-size: 14px;
  font-weight: 600;
  border-radius: 999px;
  padding: 10px 22px;
  cursor: pointer;
  transition: background 0.2s;
}
.hero-play:hover {
  background: rgba(245, 197, 107, 0.28);
}
.hero-scroll-hint {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(232, 226, 213, 0.5);
  animation: bounce 1.8s infinite;
}

/* ---------- 故事正文 ---------- */
.story {
  max-width: 640px;
  margin: 0 auto;
  padding: 12px 18px 140px;
}
.chapter {
  margin-bottom: 42px;
}
.chapter-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  padding: 0 4px;
}
.chapter-day {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #f5c56b;
  background: rgba(245, 197, 107, 0.12);
  border-radius: 6px;
  padding: 5px 10px;
  flex: none;
}
.chapter-city {
  font-size: 15px;
  color: #c8c0ae;
}
.chapter-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(245, 197, 107, 0.35), transparent);
}

.node-card {
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 18px;
  transition: transform 0.3s;
}
.node-card:hover {
  transform: translateY(-2px);
}

/* 照片墙 */
.photo-wall {
  display: grid;
  gap: 3px;
  padding: 3px;
}
.wall-1 {
  grid-template-columns: 1fr;
}
.wall-2 {
  grid-template-columns: 1fr 1fr;
}
.wall-3 {
  grid-template-columns: 1fr 1fr;
}
.wall-3 .cover {
  grid-row: span 2;
}
.photo-item {
  overflow: hidden;
  cursor: pointer;
  background: #1a2429;
}
.photo-item img {
  width: 100%;
  height: 100%;
  min-height: 120px;
  max-height: 340px;
  object-fit: cover;
  display: block;
  transition: transform 0.4s;
}
.wall-1 .photo-item img {
  max-height: 380px;
}
.photo-item:hover img {
  transform: scale(1.04);
}

.node-body {
  padding: 16px 18px 18px;
}
.node-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.node-type {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
}
.node-type.attraction {
  background: rgba(245, 197, 107, 0.15);
  color: #f5c56b;
}
.node-type.hotel {
  background: rgba(120, 180, 200, 0.15);
  color: #7fb8cc;
}
.node-type.restaurant {
  background: rgba(220, 140, 120, 0.15);
  color: #e0947c;
}
.node-type.station {
  background: rgba(140, 170, 140, 0.15);
  color: #8fb08f;
}
.node-time {
  font-size: 12px;
  color: rgba(232, 226, 213, 0.6);
}
.node-weather {
  font-size: 12px;
  color: rgba(232, 226, 213, 0.55);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.node-name {
  font-size: 19px;
  font-weight: 700;
  color: #fbf7ec;
  margin: 0 0 10px;
  letter-spacing: 1px;
}
.node-article {
  font-size: 14px;
  line-height: 2;
  color: rgba(232, 226, 213, 0.88);
  margin: 0 0 14px;
  text-align: justify;
}
.node-audio {
  display: flex;
}
.audio-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(245, 197, 107, 0.12);
  border: 1px solid rgba(245, 197, 107, 0.45);
  color: #f5c56b;
  border-radius: 999px;
  padding: 7px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}
.audio-btn.playing {
  background: rgba(245, 197, 107, 0.3);
}
.audio-btn:hover {
  background: rgba(245, 197, 107, 0.22);
}

/* 结尾 */
.story-end {
  text-align: center;
  padding: 30px 0 20px;
}
.end-line {
  width: 60px;
  height: 1px;
  background: rgba(245, 197, 107, 0.5);
  margin: 0 auto 18px;
}
.end-text {
  font-size: 15px;
  letter-spacing: 6px;
  color: rgba(232, 226, 213, 0.7);
  margin: 0 0 24px;
}
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: rgba(232, 226, 213, 0.85);
  border-radius: 999px;
  padding: 9px 20px;
  font-size: 13px;
  cursor: pointer;
}

/* ---------- BGM 控制条 ---------- */
.bgm-bar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 18px;
  display: flex;
  gap: 10px;
  z-index: 20;
}
.bgm-toggle,
.bgm-switch {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(20, 30, 34, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(245, 197, 107, 0.35);
  color: rgba(232, 226, 213, 0.9);
  border-radius: 999px;
  padding: 9px 16px;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.2s;
}
.bgm-toggle.on {
  border-color: rgba(245, 197, 107, 0.8);
  color: #f5c56b;
}

/* ---------- 灯箱 ---------- */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.lightbox-img-wrap {
  position: relative;
  max-width: 92vw;
  max-height: 88vh;
}
.lightbox-img-wrap img {
  max-width: 92vw;
  max-height: 88vh;
  object-fit: contain;
  border-radius: 8px;
}
.lb-close {
  position: absolute;
  top: -44px;
  right: 0;
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 8px;
}
.lightbox-nav {
  position: absolute;
  bottom: -48px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 16px;
}
.lb-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: #fff;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ---------- 滚动淡入 ---------- */
.reveal {
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.7s ease, transform 0.7s ease;
  transition-delay: var(--delay, 0ms);
}
.reveal.in {
  opacity: 1;
  transform: none;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(24px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes bounce {
  0%,
  100% {
    transform: translate(-50%, 0);
  }
  50% {
    transform: translate(-50%, 6px);
  }
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 120px 0;
}
</style>
