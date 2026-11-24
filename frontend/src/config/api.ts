/**
 * Centralized API configuration for VisualGuard AI frontend.
 * Reads backend base URL from environment variable VITE_API_BASE_URL
 * with fallback to http://127.0.0.1:8000.
 */

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://127.0.0.1:8000";

export const API_ENDPOINTS = {
  // Video Management
  VIDEOS_UPLOAD: `${API_BASE_URL}/api/videos/upload`,
  VIDEOS_LIST: `${API_BASE_URL}/api/videos`,
  VIDEOS_DETAIL: (mediaId: number) => `${API_BASE_URL}/api/videos/${mediaId}`,
  VIDEOS_DELETE: (mediaId: number) => `${API_BASE_URL}/api/videos/${mediaId}`,

  // Processing Management
  PROCESSING_TASKS: `${API_BASE_URL}/api/processing/tasks`,
  PROCESSING_TASK_DETAIL: (taskId: number) => `${API_BASE_URL}/api/processing/tasks/${taskId}`,
  PROCESSING_TASK_START: (taskId: number) => `${API_BASE_URL}/api/processing/tasks/${taskId}/start`,
  PROCESSING_TASK_PROGRESS: (taskId: number) => `${API_BASE_URL}/api/processing/tasks/${taskId}/progress`,
  PROCESSING_TASK_FAIL: (taskId: number) => `${API_BASE_URL}/api/processing/tasks/${taskId}/fail`,
  PROCESSING_TASK_DETECTIONS: (taskId: number) => `${API_BASE_URL}/api/processing/tasks/${taskId}/detections`,

  // Results Management
  RESULTS_ENTITIES: (mediaId: number) => `${API_BASE_URL}/api/results/media/${mediaId}/entities`,
  RESULTS_DETECTIONS: (entityId: number) => `${API_BASE_URL}/api/results/entities/${entityId}/detections`,
  RESULTS_PROCESSED: (mediaId: number) => `${API_BASE_URL}/api/results/media/${mediaId}/processed`,

  // Outputs Management
  OUTPUTS_SAVE: `${API_BASE_URL}/api/outputs/save`,
  OUTPUTS_ALL: `${API_BASE_URL}/api/outputs`,
  OUTPUTS_LIST: (mediaId: number) => `${API_BASE_URL}/api/outputs/media/${mediaId}`,
  OUTPUTS_DETAIL: (processedId: number) => `${API_BASE_URL}/api/outputs/${processedId}`,
  OUTPUTS_PREVIEW: (processedId: number) => `${API_BASE_URL}/api/outputs/${processedId}/preview`,
  OUTPUTS_DOWNLOAD: (processedId: number) => `${API_BASE_URL}/api/outputs/${processedId}/download`,
  OUTPUTS_DELETE: (processedId: number) => `${API_BASE_URL}/api/outputs/${processedId}`,
} as const;
