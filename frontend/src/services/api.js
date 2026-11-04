import axios from 'axios';
import { getRuntimeConfig } from '../config/runtime';

const runtime = getRuntimeConfig();

const api = axios.create({
  baseURL: runtime.apiBaseUrl,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(
  config => config,
  error => Promise.reject(error),
);

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  },
);

export const agentAPI = {
  startMining: data => api.post('/api/agents/start-mining', data, { timeout: 180000 }),
  parseUploadedFiles: formData => api.post('/api/agents/parse-uploaded-files', formData, {
    timeout: 180000,
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getLogs: () => api.get('/api/agents/logs'),
  getLLMHealth: () => api.get('/api/agents/llm-health', { timeout: 5000 }),
};

export const policyDocAPI = {
  saveManual: data => api.post('/api/policy-documents/manual', data),
  list: params => api.get('/api/policy-documents/', { params }),
  triggerCrawl: () => api.post('/api/policy-documents/crawl/trigger'),
  getCrawlStatus: () => api.get('/api/policy-documents/crawl/status'),
};

export const indicatorAPI = {
  getAll: status => api.get('/api/indicators/', { params: { status } }),
  getFramework: () => api.get('/api/indicators/framework'),
  getById: id => api.get(`/api/indicators/${id}`),
  create: data => api.post('/api/indicators/', data),
  update: (id, data) => api.put(`/api/indicators/${id}`, data),
  delete: id => api.delete(`/api/indicators/${id}`),
  approve: (id, comment) => api.post(`/api/indicators/${id}/approve`, { comment }),
  reject: (id, comment) => api.post(`/api/indicators/${id}/reject`, { comment }),
  getStats: () => api.get('/api/indicators/stats/summary'),
};

export const caseAPI = {
  getAll: dimension => api.get('/api/cases/', { params: { dimension } }),
  create: data => api.post('/api/cases/', data),
  generate: (indicatorName, dimension) =>
    api.post(`/api/cases/generate?indicator_name=${encodeURIComponent(indicatorName)}&dimension=${encodeURIComponent(dimension)}`),
  triggerEvolution: (content, contentType) =>
    api.post('/api/cases/evolution/trigger', { content, content_type: contentType }),
};

export default api;
