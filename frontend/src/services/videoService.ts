/**
 * Video service layer for VisualGuard AI frontend.
 * Manages video upload, file validation, progress reporting, and error handling.
 */

import { API_ENDPOINTS } from "../config/api";

export interface MediaMetadata {
  duration_seconds: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  file_size: number;
}

export interface MediaUploadResponse {
  media_id: number;
  user_id: number;
  file_name: string;
  file_path: string;
  status: string;
  metadata: MediaMetadata;
}

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

// Allowed video container extensions matching backend ALLOWED_EXTENSIONS
export const ALLOWED_VIDEO_EXTENSIONS = [".mp4", ".avi", ".mov", ".mkv", ".webm"] as const;

// Configurable maximum upload size (100 MB default matching backend MAX_UPLOAD_SIZE_MB)
export const MAX_UPLOAD_SIZE_MB = 100;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

/**
 * Validate video file format and size before uploading to the backend.
 */
export function validateVideoFile(file: File): ValidationResult {
  if (!file) {
    return { valid: false, error: "No file selected." };
  }

  // 1. Check empty file
  if (file.size === 0) {
    return { valid: false, error: "The selected video file is empty (0 bytes)." };
  }

  // 2. Check extension
  const extension = "." + (file.name.split(".").pop() || "").toLowerCase();
  const isAllowedExt = ALLOWED_VIDEO_EXTENSIONS.some((ext) => ext === extension);
  if (!isAllowedExt) {
    return {
      valid: false,
      error: `Unsupported file format '${extension}'. Allowed formats: ${ALLOWED_VIDEO_EXTENSIONS.join(", ")}`,
    };
  }

  // 3. Check maximum upload size
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(1);
    return {
      valid: false,
      error: `File size (${sizeInMB} MB) exceeds maximum allowed limit of ${MAX_UPLOAD_SIZE_MB} MB.`,
    };
  }

  return { valid: true };
}

/**
 * Upload video file to FastAPI backend using multipart/form-data.
 * Tracks upload progress via XMLHttpRequest.
 */
export function uploadVideo(
  file: File,
  userId: number = 1,
  onProgress?: (percent: number) => void
): Promise<MediaUploadResponse> {
  return new Promise((resolve, reject) => {
    // Perform client validation first
    const validation = validateVideoFile(file);
    if (!validation.valid) {
      reject(new Error(validation.error));
      return;
    }

    const xhr = new XMLHttpRequest();
    const uploadUrl = `${API_ENDPOINTS.VIDEOS_UPLOAD}?user_id=${encodeURIComponent(userId)}`;

    xhr.open("POST", uploadUrl);

    // Track upload progress
    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      let responseBody: any = null;
      try {
        responseBody = JSON.parse(xhr.responseText);
      } catch {
        // Non-JSON response
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        if (responseBody && typeof responseBody.media_id === "number") {
          resolve(responseBody as MediaUploadResponse);
        } else {
          reject(new Error("Unexpected response format from server."));
        }
      } else {
        // Extract meaningful error message from FastAPI HTTPException detail
        let message = "Upload failed.";
        if (responseBody?.detail) {
          if (typeof responseBody.detail === "string") {
            message = responseBody.detail;
          } else if (Array.isArray(responseBody.detail)) {
            message = responseBody.detail.map((err: any) => err.msg || JSON.stringify(err)).join("; ");
          } else {
            message = JSON.stringify(responseBody.detail);
          }
        } else if (xhr.status === 413) {
          message = `File size exceeds the server's maximum upload limit of ${MAX_UPLOAD_SIZE_MB} MB.`;
        } else if (xhr.status === 400) {
          message = "Bad request: The video file could not be processed by the server.";
        } else if (xhr.status >= 500) {
          message = "Server error while processing video upload. Please try again.";
        }
        reject(new Error(message));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Unable to connect to the backend server. Please check your network and server status."));
    };

    xhr.ontimeout = () => {
      reject(new Error("Upload timed out. The file may be too large or the connection too slow."));
    };

    // Construct multipart form data
    const formData = new FormData();
    formData.append("file", file, file.name);

    xhr.send(formData);
  });
}

export interface MediaItem {
  media_id: number;
  user_id: number;
  file_name?: string | null;
  file_path?: string | null;
  status?: string | null;
  duration_seconds?: number | null;
  fps?: number | null;
  width?: number | null;
  height?: number | null;
  file_size?: number | null;
  created_at?: string | null;
}

export interface MediaListResponse {
  total: number;
  items: MediaItem[];
}

/**
 * Retrieve a paginated list of uploaded videos from the backend.
 * Calls GET /api/videos.
 */
export async function listVideos(skip = 0, limit = 20): Promise<MediaListResponse> {
  const url = `${API_ENDPOINTS.VIDEOS_LIST}?skip=${skip}&limit=${limit}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || "Failed to retrieve video list.");
  }
  return response.json() as Promise<MediaListResponse>;
}

/**
 * Delete an uploaded video from backend and storage.
 */
export async function deleteUploadedVideo(mediaId: number): Promise<void> {
  const response = await fetch(API_ENDPOINTS.VIDEOS_DELETE(mediaId), {
    method: "DELETE",
  });
  if (!response.ok && response.status !== 404) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete media record #${mediaId}.`);
  }
}
