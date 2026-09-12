<template>
  <div class="login-page">
    <div class="login-header">
      <div class="logo">
        <svg viewBox="0 0 48 48" width="48" height="48">
          <path d="M24 4C14 4 6 12 6 22c0 12 18 22 18 22s18-10 18-22C42 12 34 4 24 4z" fill="#2d8f6f"/>
          <circle cx="24" cy="20" r="6" fill="#fff"/>
        </svg>
      </div>
      <h1 class="app-title">TripMemory</h1>
      <p class="app-subtitle">旅游记忆系统 · 留住每一段旅行</p>
    </div>

    <div class="login-card">
      <van-tabs v-model:active="activeTab" line-width="24px">
        <van-tab title="登录">
          <van-form @submit="onLogin">
            <van-cell-group inset>
              <van-field
                v-model="loginForm.username"
                name="username"
                label="用户名"
                placeholder="请输入用户名"
                :rules="[{ required: true, message: '请输入用户名' }]"
              />
              <van-field
                v-model="loginForm.password"
                type="password"
                name="password"
                label="密码"
                placeholder="请输入密码"
                :rules="[{ required: true, message: '请输入密码' }]"
              />
            </van-cell-group>
            <div style="margin: 16px;">
              <van-button round block type="primary" native-type="submit" :loading="loading">
                登录
              </van-button>
            </div>
          </van-form>
        </van-tab>
        <van-tab title="注册">
          <van-form @submit="onRegister">
            <van-cell-group inset>
              <van-field
                v-model="registerForm.username"
                name="username"
                label="用户名"
                placeholder="请输入用户名"
                :rules="[{ required: true, message: '请输入用户名' }]"
              />
              <van-field
                v-model="registerForm.nickname"
                name="nickname"
                label="昵称"
                placeholder="请输入昵称（选填）"
              />
              <van-field
                v-model="registerForm.password"
                type="password"
                name="password"
                label="密码"
                placeholder="请输入密码"
                :rules="[{ required: true, message: '请输入密码' }]"
              />
            </van-cell-group>
            <div style="margin: 16px;">
              <van-button round block type="primary" native-type="submit" :loading="loading">
                注册并登录
              </van-button>
            </div>
          </van-form>
        </van-tab>
      </van-tabs>
    </div>

    <div class="login-footer">
      <p>与「途迹 TripCanvas」联动，记录美好旅程</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref(0)
const loading = ref(false)

const loginForm = ref({ username: '', password: '' })
const registerForm = ref({ username: '', nickname: '', password: '' })

async function onLogin() {
  loading.value = true
  try {
    await userStore.login(loginForm.value.username, loginForm.value.password)
    showToast('登录成功')
    setTimeout(() => router.replace('/'), 100)
  } catch (e: any) {
    showToast(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}

async function onRegister() {
  loading.value = true
  try {
    await userStore.register(
      registerForm.value.username,
      registerForm.value.password,
      registerForm.value.nickname || undefined
    )
    showToast('注册成功')
    setTimeout(() => router.replace('/'), 100)
  } catch (e: any) {
    showToast(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #e8f5f0 0%, #f7f8f7 40%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px 40px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  margin-bottom: 16px;
}

.app-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1b1c;
  margin: 0 0 8px;
  letter-spacing: 2px;
}

.app-subtitle {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 8px 0 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.login-footer {
  margin-top: 40px;
  text-align: center;
}

.login-footer p {
  font-size: 12px;
  color: #9ca3af;
  margin: 0;
}
</style>
