<template>
  <div class="tm-page settings-page">
    <van-nav-bar title="设置" left-arrow @click-left="router.back()" fixed placeholder />

    <van-loading v-if="loading" style="padding: 60px 0" color="#2d8f6f" vertical>加载中…</van-loading>

    <template v-else>
      <div class="section-title">大模型 API</div>
      <div class="tm-card settings-card">
        <van-field v-model="form.llm_base_url" label="API 地址" placeholder="如 https://api.deepseek.com" />
        <van-field v-model="form.llm_api_key" label="API Key" type="password"
          :placeholder="masked.llm_api_key ? '已配置，留空不修改' : '输入 API Key'" />
        <van-field v-model="form.llm_model" label="模型名称" placeholder="如 deepseek-chat" />
        <div class="field-hint">用于 AI 游记生成；留空时使用服务器环境变量配置</div>
      </div>

      <div class="section-title">配音</div>
      <div class="tm-card settings-card">
        <van-field name="tts_voice" label="默认音色">
          <template #input>
            <select v-model="form.tts_voice" class="voice-select">
              <option v-for="(label, key) in VOICE_OPTIONS" :key="key" :value="key">{{ label }}</option>
            </select>
          </template>
        </van-field>
        <div class="field-hint">生成游记配音的默认音色，详情页可单独切换</div>
      </div>

      <div class="save-area">
        <van-button type="primary" block round color="#2d8f6f" :loading="saving" @click="onSave">保存设置</van-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { settingsApi } from '../api'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)

const VOICE_OPTIONS: Record<string, string> = {
  xiaoxiao: '晓晓（女声·温暖）',
  xiaoyi: '晓伊（女声·活泼）',
  yunjian: '云健（男声·激情）',
  yunxi: '云希（男声·阳光）',
}

// 表单：api_key 类字段单独跟踪是否已修改（脱敏值不回传）
const form = reactive({
  llm_base_url: '',
  llm_api_key: '',  // 用户输入的新 key，空表示不修改
  llm_model: '',
  tts_voice: 'xiaoxiao',
})
const masked = reactive({
  llm_api_key: false, // 后端返回了脱敏值（说明已配置）
})

async function load() {
  loading.value = true
  try {
    const res: any = await settingsApi.get()
    form.llm_base_url = res.llm_base_url
    form.llm_model = res.llm_model
    form.tts_voice = res.tts_voice || 'xiaoxiao'
    masked.llm_api_key = res.llm_api_key === '••••••••'
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (saving.value) return
  saving.value = true
  try {
    const payload: any = {
      llm_base_url: form.llm_base_url.trim(),
      llm_model: form.llm_model.trim(),
      tts_voice: form.tts_voice,
    }
    // 只有用户输入了新 key 才传，空字符串表示清除（用户主动清空）
    if (form.llm_api_key) payload.llm_api_key = form.llm_api_key.trim()
    else if (!masked.llm_api_key) payload.llm_api_key = ''

    const res: any = await settingsApi.update(payload)
    masked.llm_api_key = res.llm_api_key === '••••••••'
    form.llm_api_key = ''
    showToast('设置已保存')
  } catch (e) {
    showToast((e as Error).message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.settings-page {
  padding-top: 8px;
}
.section-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--tm-ink-3);
  margin: 16px 2px 6px;
  letter-spacing: 0.5px;
}
.settings-card {
  padding: 4px 0;
}
.settings-card :deep(.van-cell) {
  padding: 14px 16px;
}
.field-hint {
  font-size: 11px;
  color: var(--tm-ink-3);
  padding: 0 16px 10px;
  line-height: 1.5;
}
.voice-select {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--tm-ink-2);
  text-align: right;
  appearance: auto;
}
.save-area {
  padding: 24px 0 calc(24px + env(safe-area-inset-bottom));
}
</style>
