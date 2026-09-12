<template>
  <div class="tm-page">
    <div class="sync-header">
      <button class="back-btn" @click="router.back()">
        <van-icon name="arrow-left" />
      </button>
      <h1 class="page-title">从途迹同步</h1>
    </div>

    <div class="sync-intro tm-card">
      <div class="intro-icon">
        <svg viewBox="0 0 48 48" width="40" height="40">
          <path d="M24 4C14 4 6 12 6 22c0 12 18 22 18 22s18-10 18-22C42 12 34 4 24 4z" fill="#2d8f6f"/>
          <circle cx="24" cy="20" r="6" fill="#fff"/>
        </svg>
      </div>
      <div class="intro-text">
        <h3>同步途迹 TripCanvas 行程</h3>
        <p>输入途迹系统中的行程ID，将已完成的旅行行程同步到记忆系统，后续可关联照片、生成游记。</p>
      </div>
    </div>

    <div class="sync-form tm-card">
      <van-field
        v-model="tripId"
        label="行程ID"
        placeholder="请输入途迹系统中的行程ID"
        type="number"
      />
      <div class="form-hint">
        <p>在途迹 TripCanvas 系统的行程详情页URL中可以找到行程ID</p>
      </div>
      <button
        class="tm-btn tm-btn-primary sync-btn"
        :disabled="!tripId || syncing"
        @click="onSync"
      >
        {{ syncing ? '同步中…' : '开始同步' }}
      </button>
    </div>

    <div v-if="syncResult" class="sync-result tm-card">
      <div class="result-icon success">
        <van-icon name="checked" size="32" />
      </div>
      <h3>同步成功</h3>
      <p>{{ syncResult.title }}</p>
      <button class="tm-btn tm-btn-primary" @click="router.push(`/memory/${syncResult.id}`)">
        查看记忆行程
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { memoryApi } from '../api'

const router = useRouter()
const tripId = ref('')
const syncing = ref(false)
const syncResult = ref<any>(null)

async function onSync() {
  if (!tripId.value) return
  syncing.value = true
  syncResult.value = null
  try {
    const res: any = await memoryApi.syncFromTripCanvas(Number(tripId.value))
    syncResult.value = res
    showToast('同步成功')
  } catch (e: any) {
    showToast(e.response?.data?.detail || '同步失败，请检查连接配置')
  } finally {
    syncing.value = false
  }
}
</script>

<style scoped>
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

.sync-intro {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.intro-icon {
  flex-shrink: 0;
}

.intro-text h3 {
  font-size: 15px;
  margin: 0 0 6px;
  color: var(--tm-ink);
}

.intro-text p {
  font-size: 13px;
  color: var(--tm-ink-2);
  margin: 0;
  line-height: 1.6;
}

.sync-form {
  margin-top: 12px;
}

.form-hint {
  padding: 8px 16px;
}

.form-hint p {
  font-size: 12px;
  color: var(--tm-ink-3);
  margin: 0;
}

.sync-btn {
  width: calc(100% - 32px);
  margin: 8px 16px 0;
  padding: 12px;
}

.sync-result {
  text-align: center;
  margin-top: 12px;
}

.result-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
}

.result-icon.success {
  background: var(--tm-primary-light);
  color: var(--tm-primary);
}

.sync-result h3 {
  font-size: 16px;
  margin: 0 0 8px;
}

.sync-result p {
  font-size: 13px;
  color: var(--tm-ink-2);
  margin: 0 0 16px;
}

.sync-result .tm-btn {
  width: 100%;
}
</style>
