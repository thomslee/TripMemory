<template>
  <div class="tm-page">
    <div class="page-header">
      <button class="back-btn" @click="router.back()">
        <van-icon name="arrow-left" />
      </button>
      <h1 class="page-title">TripCanvas 账号绑定</h1>
    </div>

    <div class="intro tm-card">
      <div class="intro-icon">
        <van-icon name="link-o" size="26" color="#2d8f6f" />
      </div>
      <div class="intro-text">
        <h3>为什么要绑定？</h3>
        <p>绑定你的途迹 TripCanvas 账号后，同步行程时将使用该账号访问 TripCanvas，可以同步你自己账号下的已定稿行程（未绑定时仅能同步服务账号的行程）。</p>
      </div>
    </div>

    <!-- 未绑定：绑定表单 -->
    <div v-if="!binding.bound" class="form tm-card">
      <van-field
        v-model="form.username"
        label="途迹账号"
        placeholder="TripCanvas 登录用户名"
        clearable
      />
      <van-field
        v-model="form.password"
        type="password"
        label="途迹密码"
        placeholder="TripCanvas 登录密码"
        clearable
      />
      <button
        class="tm-btn tm-btn-primary save-btn"
        :disabled="!form.username || !form.password || saving"
        @click="onBind"
      >
        {{ saving ? '绑定中…' : '保存绑定' }}
      </button>
      <p class="form-note">绑定前会校验账号密码有效性，密码加密存储。</p>
    </div>

    <!-- 已绑定：状态展示 -->
    <div v-else class="bound tm-card">
      <div class="bound-item">
        <span class="bound-label">已绑定账号</span>
        <span class="bound-value">{{ binding.tripcanvas_username }}</span>
      </div>
      <p class="bound-hint">同步行程时将使用该账号访问 TripCanvas</p>
      <button class="tm-btn tm-btn-danger save-btn" :disabled="saving" @click="onUnbind">
        {{ saving ? '解绑中…' : '解绑账号' }}
      </button>
      <p class="form-note" style="margin-top: 8px;">解绑后恢复使用系统服务账号同步。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { authApi } from '../api'

const router = useRouter()
const binding = ref<{ bound: boolean; tripcanvas_username: string }>({ bound: false, tripcanvas_username: '' })
const form = ref({ username: '', password: '' })
const saving = ref(false)

async function loadBinding() {
  try {
    const res: any = await authApi.getTripCanvasBinding()
    binding.value = res
  } catch {
    showToast('获取绑定状态失败')
  }
}

async function onBind() {
  saving.value = true
  try {
    const res: any = await authApi.bindTripCanvas(form.value.username, form.value.password)
    binding.value = { bound: true, tripcanvas_username: res.tripcanvas_username }
    form.value = { username: '', password: '' }
    showToast('绑定成功')
  } catch (e: any) {
    showToast(e.response?.data?.detail || '绑定失败')
  } finally {
    saving.value = false
  }
}

async function onUnbind() {
  saving.value = true
  try {
    await authApi.unbindTripCanvas()
    binding.value = { bound: false, tripcanvas_username: '' }
    showToast('已解绑')
  } catch {
    showToast('解绑失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadBinding)
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.back-btn {
  border: none;
  background: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--tm-ink);
  padding: 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--tm-ink);
}

.intro {
  display: flex;
  gap: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.intro-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 20px;
  background: rgba(45, 143, 111, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.intro-text h3 {
  font-size: 15px;
  margin: 0 0 6px;
  color: var(--tm-ink);
}

.intro-text p {
  font-size: 13px;
  line-height: 1.6;
  color: var(--tm-ink-2);
  margin: 0;
}

.form,
.bound {
  padding: 8px 16px 16px;
}

.save-btn {
  margin-top: 14px;
  width: 100%;
}

.form-note {
  font-size: 12px;
  color: var(--tm-ink-3);
  margin: 10px 0 0;
  text-align: center;
}

.bound-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}

.bound-label {
  font-size: 14px;
  color: var(--tm-ink);
}

.bound-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--tm-ink);
}

.bound-hint {
  font-size: 12px;
  color: var(--tm-ink-3);
  margin: 10px 0 0;
}
</style>
