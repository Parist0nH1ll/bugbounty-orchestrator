/**
 * API 请求封装 - Axios 实例
 */
import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message;
    console.error("[API Error]", message);
    return Promise.reject(error);
  }
);

export default api;

// -------- 端点方法 --------

/** 健康检查 */
export const apiHealth = () => api.get("/health");

/** 上传域名文件 */
export const uploadDomains = (file) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/upload/domains", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

/** 上传域名文本 */
export const uploadDomainsText = (text) => {
  const blob = new Blob([text], { type: "text/plain" });
  const file = new File([blob], "domains.txt");
  return uploadDomains(file);
};

/** 获取任务列表 */
export const getTasks = (params) => api.get("/tasks/", { params });

/** 获取任务详情 */
export const getTask = (taskId) => api.get(`/tasks/${taskId}`);

/** 取消任务 */
export const cancelTask = (taskId) => api.post(`/tasks/${taskId}/cancel`);

/** 获取筛选规则 */
export const getRules = () => api.get("/rules/");

/** 创建筛选规则 */
export const createRule = (data) => api.post("/rules/", data);

/** 更新筛选规则 */
export const updateRule = (ruleId, data) => api.put(`/rules/${ruleId}`, data);

/** 删除筛选规则 */
export const deleteRule = (ruleId) => api.delete(`/rules/${ruleId}`);

/** 发送 Agent 指令 */
export const sendAgentCommand = (taskId, prompt) =>
  api.post("/agent/command", { task_id: taskId, prompt });

/** 获取漏洞报告 */
export const getReport = (taskId) => api.get(`/reports/${taskId}`);

/** 导出报告 CSV */
export const exportReportCsv = (taskId) =>
  api.get(`/reports/${taskId}/export`, { responseType: "blob" });
