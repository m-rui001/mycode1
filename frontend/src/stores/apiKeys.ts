// 简化后的apiKeys.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { AgentType } from "@/utils/enum";
import type { ModelConfig } from "@/utils/interface";

export const useApiKeyStore = defineStore('apiKeys', () => {
  // 保留基础配置存储，移除前端校验相关计算属性
  const coordinatorConfig = ref<ModelConfig>({
    apiKey: '',
    baseUrl: '',
    modelId: ''
  });
  
  const modelerConfig = ref<ModelConfig>({
    apiKey: '',
    baseUrl: '',
    modelId: ''
  });
  
  const coderConfig = ref<ModelConfig>({
    apiKey: '',
    baseUrl: '',
    modelId: ''
  });
  
  const writerConfig = ref<ModelConfig>({
    apiKey: '',
    baseUrl: '',
    modelId: ''
  });

  // 保留基础setter方法
  function setCoordinatorConfig(config: ModelConfig) {
    coordinatorConfig.value = { ...config };
  }
  function setModelerConfig(config: ModelConfig) {
    modelerConfig.value = { ...config };
  }
  function setCoderConfig(config: ModelConfig) {
    coderConfig.value = { ...config };
  }
  function setWriterConfig(config: ModelConfig) {
    writerConfig.value = { ...config };
  }

  function getAllAgentConfigs() {
    return {
      [AgentType.COORDINATOR]: coordinatorConfig.value,
      [AgentType.MODELER]: modelerConfig.value,
      [AgentType.CODER]: coderConfig.value,
      [AgentType.WRITER]: writerConfig.value,
    };
  }

  function resetAll() {
    coordinatorConfig.value = { apiKey: '', baseUrl: '', modelId: '' };
    modelerConfig.value = { apiKey: '', baseUrl: '', modelId: '' };
    coderConfig.value = { apiKey: '', baseUrl: '', modelId: '' };
    writerConfig.value = { apiKey: '', baseUrl: '', modelId: '' };
  }

  return {
    coordinatorConfig,
    modelerConfig,
    coderConfig,
    writerConfig,
    setCoordinatorConfig,
    setModelerConfig,
    setCoderConfig,
    setWriterConfig,
    getAllAgentConfigs,
    resetAll
  }
}, {
  persist: true
});