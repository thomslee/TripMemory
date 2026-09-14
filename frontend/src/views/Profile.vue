<template>
  <div class="tm-page profile-page">
    <van-nav-bar title="我的" left-arrow @click-left="router.back()" fixed placeholder />

    <!-- 用户信息卡片 -->
    <div class="profile-card">
      <div class="profile-avatar">
        {{ (userStore.user?.nickname || userStore.user?.username || '?').charAt(0).toUpperCase() }}
      </div>
      <div class="profile-info">
        <div class="profile-name">{{ userStore.user?.nickname || userStore.user?.username }}</div>
        <div class="profile-sub">
          <span>@{{ userStore.user?.username }}</span>
          <span class="role-badge" :class="userStore.user?.role">
            {{ userStore.user?.role === 'admin' ? '管理员' : '普通用户' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="tm-card section">
      <div class="section-title">修改密码</div>
      <van-field v-model="oldPwd" label="原密码" type="password" placeholder="请输入原密码" />
      <van-field v-model="newPwd" label="新密码" type="password" placeholder="至少 4 位" />
      <van-field v-model="confirmPwd" label="确认新密码" type="password" placeholder="再次输入新密码" />
      <button class="tm-btn tm-btn-primary primary-btn" :disabled="pwdLoading" @click="onChangePwd">
        {{ pwdLoading ? '提交中…' : '确认修改' }}
      </button>
    </div>

    <!-- 管理员：用户管理 -->
    <div v-if="userStore.isAdmin" class="tm-card section">
      <div class="section-title">用户管理</div>
      <div v-if="usersLoading" class="loading-tip">加载中…</div>
      <div v-else class="user-list">
        <div v-for="u in users" :key="u.id" class="user-row">
          <div class="user-row-info">
            <span class="user-row-name">{{ u.nickname || u.username }}</span>
            <span class="user-row-sub">@{{ u.username }} · {{ u.role === 'admin' ? '管理员' : '普通用户' }}</span>
          </div>
          <div class="user-row-actions">
            <button v-if="u.role !== 'admin'" class="role-btn admin" @click="onChangeRole(u, 'admin')">设为管理员</button>
            <button v-if="u.role !== 'user'" class="role-btn user" @click="onChangeRole(u, 'user')">降为普通用户</button>
            <span v-if="u.id === userStore.user?.id" class="self-tag">当前用户</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 退出登录 -->
    <button class="logout-btn" @click="onLogout">退出登录</button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { useUserStore } from '../stores/user'
import { authApi, adminApi } from '../api'

const router = useRouter()
const userStore = useUserStore()

const isAdmin = computed(() => userStore.user?.role === 'admin')

// 修改密码
const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdLoading = ref(false)

async function onChangePwd() {
  if (!oldPwd.value || !newPwd.value || !confirmPwd.value) {
    showToast('请填写完整')
    return
  }
  if (newPwd.value !== confirmPwd.value) {
    showToast('两次输入的新密码不一致')
    return
  }
  pwdLoading.value = true
  try {
    await authApi.changePassword(oldPwd.value, newPwd.value)
    oldPwd.value = newPwd.value = confirmPwd.value = ''
    showToast('密码已修改')
  } catch (e: any) {
    showToast(e.response?.data?.detail || e.message || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

// 用户管理（管理员）
const users = ref<any[]>([])
const usersLoading = ref(false)

async function loadUsers() {
  usersLoading.value = true
  try {
    const res: any = await adminApi.listUsers()
    users.value = res
  } catch (e: any) {
    showToast(e.response?.data?.detail || '加载失败')
  } finally {
    usersLoading.value = false
  }
}

async function onChangeRole(u: any, role: string) {
  if (u.id === userStore.user?.id) {
    showToast('不能修改自己的角色')
    return
  }
  try {
    await showConfirmDialog({
      title: '修改角色',
      message: `确定将「${u.username}」改为${role === 'admin' ? '管理员' : '普通用户'}吗？`,
      confirmButtonColor: '#2d8f6f',
    })
    const res: any = await adminApi.updateRole(u.id, role)
    u.role = res.role
    showToast('已更新')
  } catch {
    /* 取消 */
  }
}

function onLogout() {
  userStore.logout()
  router.replace('/login')
}

onMounted(() => {
  if (isAdmin.value) loadUsers()
})
</script>

<style scoped>
.profile-page {
  padding-top: 8px;
  padding-bottom: 40px;
}
.profile-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(135deg, #2d8f6f, #4aa88a);
  border-radius: var(--tm-radius);
  padding: 20px;
  margin-bottom: 14px;
  color: #fff;
}
.profile-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
}
.profile-info {
  flex: 1;
}
.profile-name {
  font-size: 18px;
  font-weight: 600;
}
.profile-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 13px;
  opacity: 0.9;
}
.role-badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.22);
}
.section {
  padding: 14px 8px 16px;
}
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--tm-ink);
  margin: 0 8px 12px;
}
.primary-btn {
  width: 100%;
  margin-top: 14px;
}
.loading-tip {
  padding: 20px;
  text-align: center;
  color: var(--tm-ink-3);
  font-size: 13px;
}
.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 8px;
  border-bottom: 1px solid var(--tm-line);
}
.user-row:last-child {
  border-bottom: none;
}
.user-row-name {
  font-size: 14px;
  color: var(--tm-ink);
  display: block;
}
.user-row-sub {
  font-size: 12px;
  color: var(--tm-ink-3);
  display: block;
  margin-top: 2px;
}
.user-row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.role-btn {
  border: none;
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
}
.role-btn.admin {
  background: var(--tm-primary-light);
  color: var(--tm-primary);
}
.role-btn.user {
  background: #fef2f2;
  color: #dc2626;
}
.self-tag {
  font-size: 11px;
  color: var(--tm-ink-3);
}
.logout-btn {
  width: 100%;
  margin-top: 16px;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: #fff;
  color: #dc2626;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
</style>
