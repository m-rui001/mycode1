<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useApiKeyStore } from '@/stores/apiKeys'
import { saveApiConfig } from '@/apis/apiKeyApi'

const apiKeyStore = useApiKeyStore()

// 本地表单数据
const form = ref<{
  coordinator: { apiKey: string; baseUrl: string; modelId: string };
  modeler: { apiKey: string; baseUrl: string; modelId: string };
  coder: { apiKey: string; baseUrl: string; modelId: string };
  writer: { apiKey: string; baseUrl: string; modelId: string };
}>({
  coordinator: { apiKey: '', baseUrl: '', modelId: '' },
  modeler: { apiKey: '', baseUrl: '', modelId: '' },
  coder: { apiKey: '', baseUrl: '', modelId: '' },
  writer: { apiKey: '', baseUrl: '', modelId: '' }
})

// 模型配置列表
const modelConfigs = computed(() => [
  { key: 'coordinator', label: '协调者模型配置' },
  { key: 'modeler', label: '建模手模型配置' },
  { key: 'coder', label: '代码手模型配置' },
  { key: 'writer', label: '论文手模型配置' }
])

// 从 store 加载数据到表单
const loadFromStore = () => {
  form.value.coordinator = { ...apiKeyStore.coordinatorConfig }
  form.value.modeler = { ...apiKeyStore.modelerConfig }
  form.value.coder = { ...apiKeyStore.coderConfig }
  form.value.writer = { ...apiKeyStore.writerConfig }
}

// 保存表单数据到 store 和后端
const saveToStore = async () => {
  // 保存到前端 store
  apiKeyStore.setCoordinatorConfig(form.value.coordinator)
  apiKeyStore.setModelerConfig(form.value.modeler)
  apiKeyStore.setCoderConfig(form.value.coder)
  apiKeyStore.setWriterConfig(form.value.writer)

  // 保存到后端
  try {
    await saveApiConfig({
      coordinator: form.value.coordinator,
      modeler: form.value.modeler,
      coder: form.value.coder,
      writer: form.value.writer
    })
  } catch (error) {
    console.error('保存配置到后端失败:', error)
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadFromStore()
})

// 定义 emits 和 props
const emit = defineEmits<{ (e: 'update:open', value: boolean): void }>()
const props = defineProps<{ open: boolean }>()

// 更新 open 状态
const updateOpen = (value: boolean) => {
  emit('update:open', value)
}

// 保存并关闭
const saveAndClose = async () => {
  await saveToStore()
  updateOpen(false)
}

// 模型链接配置
const links = {
  "DeepSeek": { 
    "url": "https://platform.deepseek.com/api_keys",
    "key": "DeepSeek",
    "BaseURL": "https://api.deepseek.com",
    "ModelID": "deepseek/deepseek-chat"
  },
  "硅基流动": {
    "url": "https://cloud.siliconflow.cn/i/UIb4Enf4",
    "key": "硅基流动",
    "BaseURL": "https://api.siliconflow.cn",
    "ModelID": "openai/deepseek-ai/DeepSeek-V3"
  },
  "Sophnet": {
    "url": "https://www.sophnet.com/#?code=AZBSFG",
    "key": "Sophnet",
    "BaseURL": "https://www.sophnet.com/api/open-apis",
    "ModelID": "openai/DeepSeek-V3-Fast"
  },
  "OpenAI": {
    "url": "https://platform.openai.com/api_keys",
    "key": "OpenAI",
    "BaseURL": "https://api.openai.com",
    "ModelID": "openai/gpt-4o"
  }
}
</script>

<template>
  <Dialog :open="props.open" @update:open="updateOpen">
    <DialogContent class="max-w-xl max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>API Key 设置</DialogTitle>
        <DialogDescription>
          为每个 Agent 配置合适模型
          <br>
          <div class="mt-2 space-y-2">
            <div v-for="link in links" :key="link.key">
              <div class="flex flex-col gap-1">
                <a :href="link.url" target="_blank" class="text-blue-600 hover:text-blue-800 underline text-xs">
                  {{ link.key }}
                </a>
                <div class="text-xs text-muted-foreground">
                  Base URL: {{ link.BaseURL }}
                </div>
                <div class="text-xs text-muted-foreground">
                  Model ID: {{ link.ModelID }}
                </div>
              </div>
            </div>
          </div>
          <div class="mt-2">
            <a href="https://docs.litellm.ai/docs/providers" target="_blank"
              class="text-blue-600 hover:text-blue-800 underline text-xs">
              查看更多模型配置
            </a>
          </div>
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-4 py-2">
        <!-- 模型配置项 -->
        <div v-for="config in modelConfigs" :key="config.key" class="space-y-2">
          <h3 class="text-sm font-medium">{{ config.label }}</h3>
          <div class="grid grid-cols-1 gap-2">
            <div class="space-y-1">
              <Label :for="`${config.key}-api-key`" class="text-xs text-muted-foreground">API Key</Label>
              <Input 
                :id="`${config.key}-api-key`" 
                v-model.trim="(form as any)[config.key].apiKey" 
                type="password"
                placeholder="请输入 API Key" 
                class="h-7 text-xs" 
              />
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div class="space-y-1">
                <Label :for="`${config.key}-base-url`" class="text-xs text-muted-foreground">Base URL</Label>
                <Input 
                  :id="`${config.key}-base-url`" 
                  v-model.trim="(form as any)[config.key].baseUrl"
                  placeholder="例如: https://api.deepseek.com" 
                  class="h-7 text-xs" 
                />
              </div>
              <div class="space-y-1">
                <Label :for="`${config.key}-model-id`" class="text-xs text-muted-foreground">Model ID</Label>
                <Input 
                  :id="`${config.key}-model-id`" 
                  v-model.trim="(form as any)[config.key].modelId"
                  placeholder="例如: deepseek/deepseek-chat" 
                  class="h-7 text-xs" 
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-end items-center pt-3 border-t">
        <div class="flex space-x-2">
          <Button variant="outline" @click="updateOpen(false)" class="h-7 text-xs px-3">
            取消
          </Button>
          <Button @click="saveAndClose" class="h-7 text-xs px-3">
            保存
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
