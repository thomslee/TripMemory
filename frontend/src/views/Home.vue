<template>
  <div class="tm-page">
    <div class="home-header">
      <div class="header-top">
        <h1 class="page-title">TripMemory</h1>
        <div class="user-info" @click="showUserMenu = true">
          <span class="user-name">{{ userStore.user?.nickname || userStore.user?.username }}</span>
          <van-icon name="setting-o" size="18" />
        </div>
      </div>
      <p class="page-desc">记录每一段旅行的美好回忆</p>
    </div>

    <div class="action-row">
      <button class="tm-btn tm-btn-primary action-btn" @click="router.push('/sync')">
        <van-icon name="down" />
        从途迹同步
      </button>
    </div>

    <div v-if="loading" class="loading-tip">加载中…</div>

    <div v-else-if="trips.length === 0" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 64 64" width="64" height="64">
          <rect x="8" y="12" width="48" height="40" rx="4" fill="#e5e7eb"/>
          <circle cx="20" cy="24" r="4" fill="#9ca3af"/>
          <path d="M8 44l16-12 12 8 12-10 8 6v6H8z" fill="#d1d5db"/>
        </svg>
      </div>
      <p class="empty-text">还没有记忆行程</p>
      <p class="empty-hint">点击上方"从途迹同步"，导入已完成的旅行</p>
    </div>

    <div v-else class="trip-list">
      <div
        v-for="trip in trips"
        :key="trip.id"
        class="trip-card"
        @click="router.push(`/memory/${trip.id}`)"
      >
        <div class="trip-cover">
          <div v-if="trip.cover_image" class="cover-img" :style="{ backgroundImage: `url(${trip.cover_image})` }"></div>
          <div v-else class="cover-placeholder">
            <van-icon name="photo-o" size="32" />
          </div>
          <div class="trip-badge">{{ trip.total_days }}天</div>
        </div>
        <div class="trip-info">
          <h3 class="trip-title">{{ trip.title }}</h3>
          <div class="trip-meta">
            <span class="meta-item"><van-icon name="location-o" /> {{ trip.dest_city || '未设置' }}</span>
            <span class="meta-item"><van-icon name="photo-o" /> {{ trip.photo_count }}张照片</span>
          </div>
          <div class="trip-date">{{ trip.depart_date || '日期未设置' }}</div>
        </div>
      </div>
    </div>

    <van-action-sheet v-model:show="showUserMenu" title="用户中心">
      <van-cell title="设置" is-link @click="showUserMenu = false" />
      <van-cell title="退出登录" is-link @click="onLogout" />
    </van-action-sheet>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '../stores/user'
import { memoryApi } from '../api'

const router = useRouter()
const userStore = useUserStore()

const trips = ref<any[]>([])
const loading = ref(true)
const showUserMenu = ref(false)

async function loadTrips() {
  loading.value = true
  try {
    const res: any = await memoryApi.list()
    trips.value = res
  } catch (e) {
    showToast('加载失败')
  } finally {
    loading.value = false
  }
}

function onLogout() {
  userStore.logout()
  showUserMenu.value = false
  router.replace('/login')
}

onMounted(loadTrips)
</script>

<style scoped>
.home-header {
  margin-bottom: 20px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: var(--tm-ink);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--tm-card);
  border-radius: 20px;
  cursor: pointer;
}

.user-name {
  font-size: 13px;
  color: var(--tm-ink-2);
}

.page-desc {
  font-size: 13px;
  color: var(--tm-ink-3);
  margin: 8px 0 0;
}

.action-row {
  margin-bottom: 16px;
}

.action-btn {
  width: 100%;
  padding: 14px;
  font-size: 15px;
}

.loading-tip {
  text-align: center;
  padding: 40px;
  color: var(--tm-ink-3);
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-text {
  font-size: 16px;
  color: var(--tm-ink-2);
  margin: 0 0 8px;
}

.empty-hint {
  font-size: 13px;
  color: var(--tm-ink-3);
  margin: 0;
}

.trip-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trip-card {
  background: var(--tm-card);
  border-radius: var(--tm-radius);
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s;
}

.trip-card:active {
  transform: scale(0.98);
}

.trip-cover {
  position: relative;
  height: 140px;
  background: #f0f0f0;
}

.cover-img {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
}

.trip-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.trip-info {
  padding: 14px;
}

.trip-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--tm-ink);
}

.trip-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
}

.meta-item {
  font-size: 12px;
  color: var(--tm-ink-2);
  display: flex;
  align-items: center;
  gap: 3px;
}

.trip-date {
  font-size: 12px;
  color: var(--tm-ink-3);
}
</style>
