import { API_ENDPOINTS } from "../config/api";

export interface ProcessedMediaItem {
  processed_id: number;
  media_id: number;
  output_path: string | null;
  output_type: string | null;
}

export interface ProcessedMediaListResponse {
  total: number;
  items: ProcessedMediaItem[];
}

/**
 * Retrieve a paginated list of all processed output videos.
 * Calls GET /api/outputs
 */
export async function listAllOutputs(
  skip = 0,
  limit = 50
): Promise<ProcessedMediaListResponse> {
  const url = `${API_ENDPOINTS.OUTPUTS_ALL}?skip=${skip}&limit=${limit}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody?.detail || "Failed to retrieve processed outputs.");
  }

  return response.json() as Promise<ProcessedMediaListResponse>;
}

/**
 * Get direct streaming URL for video preview.
 */
export function getOutputPreviewUrl(processedId: number): string {
  return API_ENDPOINTS.OUTPUTS_PREVIEW(processedId);
}

/**
 * Get download URL for processed video.
 */
export function getOutputDownloadUrl(processedId: number): string {
  return API_ENDPOINTS.OUTPUTS_DOWNLOAD(processedId);
}

/**
 * Delete a processed output by ID.
 */
export async function deleteOutput(processedId: number): Promise<void> {
  const response = await fetch(API_ENDPOINTS.OUTPUTS_DELETE(processedId), {
    method: "DELETE",
  });

  if (!response.ok && response.status !== 404) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody?.detail || `Failed to delete output #${processedId}.`);
  }
}
