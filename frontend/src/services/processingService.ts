/**
 * Processing service layer for VisualGuard AI frontend.
 * Manages processing task creation, status retrieval, and error handling
 * with the FastAPI backend (/api/processing/tasks).
 */

import { API_ENDPOINTS } from "../config/api";

export type ProtectionType = "faces" | "number_plates" | "both";

export interface CreateProcessingTaskPayload {
  media_id: number;
  protection_type: ProtectionType;
  blur_intensity?: number | null;
}

export interface ProcessingTaskResponse {
  task_id: number;
  media_id: number;
  status: string;
  progress: number | null;
  protection_type: ProtectionType;
  blur_intensity: number | null;
  error_message: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * Create a new processing task associated with an uploaded media record.
 * Calls POST /api/processing/tasks.
 */
export async function createProcessingTask(
  payload: CreateProcessingTaskPayload
): Promise<ProcessingTaskResponse> {
  // Validate input parameters
  if (!payload.media_id || payload.media_id <= 0) {
    throw new Error("Invalid media ID. Please upload a video first.");
  }

  const validProtectionTypes: ProtectionType[] = ["faces", "number_plates", "both"];
  if (!validProtectionTypes.includes(payload.protection_type)) {
    throw new Error(
      `Invalid protection type '${payload.protection_type}'. Expected one of: ${validProtectionTypes.join(", ")}`
    );
  }

  if (
    payload.blur_intensity !== undefined &&
    payload.blur_intensity !== null &&
    (payload.blur_intensity < 0 || payload.blur_intensity > 100)
  ) {
    throw new Error("Blur intensity must be between 0 and 100.");
  }

  const requestBody = {
    media_id: payload.media_id,
    protection_type: payload.protection_type,
    blur_intensity: payload.blur_intensity ?? null,
  };

  let response: Response;
  try {
    response = await fetch(API_ENDPOINTS.PROCESSING_TASKS, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(requestBody),
    });
  } catch {
    throw new Error(
      "Unable to connect to the backend server. Please verify the server is running."
    );
  }

  let responseBody: any = null;
  try {
    responseBody = await response.json();
  } catch {
    // Non-JSON response
  }

  if (response.ok) {
    if (!responseBody || typeof responseBody.task_id !== "number") {
      throw new Error("Unexpected response format received from processing task endpoint.");
    }
    return responseBody as ProcessingTaskResponse;
  }

  // Format meaningful error message from backend
  let message = "Failed to create processing task.";
  if (responseBody?.detail) {
    if (typeof responseBody.detail === "string") {
      message = responseBody.detail;
    } else if (Array.isArray(responseBody.detail)) {
      message = responseBody.detail
        .map((err: any) => err.msg || JSON.stringify(err))
        .join("; ");
    } else {
      message = JSON.stringify(responseBody.detail);
    }
  } else if (response.status === 404) {
    message = `Media #${payload.media_id} not found. Please upload your video again.`;
  } else if (response.status === 422) {
    message = "Request validation failed. Please check the selected options.";
  } else if (response.status >= 500) {
    message = "Server error while creating processing task. Please try again.";
  }

  throw new Error(message);
}

export interface ProcessingTaskListResponse {
  total: number;
  items: ProcessingTaskResponse[];
}

/**
 * Retrieve a paginated list of processing tasks from the backend.
 * Calls GET /api/processing/tasks.
 */
export async function listProcessingTasks(skip = 0, limit = 20): Promise<ProcessingTaskListResponse> {
  const url = `${API_ENDPOINTS.PROCESSING_TASKS}?skip=${skip}&limit=${limit}`;
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || "Failed to retrieve processing task list.");
  }
  return response.json() as Promise<ProcessingTaskListResponse>;
}

/**
 * Retrieve status and details of an existing processing task.
 * Calls GET /api/processing/tasks/{task_id}.
 */
export async function getProcessingTask(
  taskId: number
): Promise<ProcessingTaskResponse> {
  if (!taskId || taskId <= 0) {
    throw new Error("Invalid task ID.");
  }

  const response = await fetch(API_ENDPOINTS.PROCESSING_TASK_DETAIL(taskId), {
    headers: { Accept: "application/json" },
  });

  const responseBody = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      responseBody?.detail || `Failed to retrieve processing task #${taskId}.`
    );
  }

  return responseBody as ProcessingTaskResponse;
}
