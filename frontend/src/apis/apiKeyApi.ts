// 简化后的apiKeyApi.ts
import request from "@/utils/request";

// 仅保留保存API配置接口（直接调用后端，不做前端校验）
export interface SaveApiConfigRequest {
  coordinator: {
    apiKey: string;
    baseUrl: string;
    modelId: string;
  };
  modeler: {
    apiKey: string;
    baseUrl: string;
    modelId: string;
  };
  coder: {
    apiKey: string;
    baseUrl: string;
    modelId: string;
  };
  writer: {
    apiKey: string;
    baseUrl: string;
    modelId: string;
  };
}

export function saveApiConfig(params: SaveApiConfigRequest) {
  return request.post<{ success: boolean; message: string }>("/save-api-config", params);
}