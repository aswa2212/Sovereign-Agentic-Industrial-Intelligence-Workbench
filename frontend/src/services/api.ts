/**
 * Centralized REST API client for SIH26117 Workbench.
 * Encapsulates base URL handling, timeouts, error parsing, and request logging.
 */

const API_BASE = '/api/v1';

export class ApiError extends Error {
  code: string;
  status: number;
  details?: Record<string, any>;

  constructor(message: string, code = 'API_ERROR', status = 500, details?: Record<string, any>) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs = 30000
): Promise<T> {
  const url = endpoint.startsWith('http') || endpoint.startsWith('/health')
    ? endpoint
    : `${API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    // Don't set Content-Type if FormData is used (browser sets multipart boundary)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(id);

    if (!response.ok) {
      let errorData: any = null;
      try {
        errorData = await response.json();
      } catch {
        errorData = { message: response.statusText };
      }

      const errDetail = errorData?.detail || errorData?.error || errorData;
      const message = typeof errDetail === 'string'
        ? errDetail
        : errDetail?.message || `HTTP ${response.status}: ${response.statusText}`;
      const code = errDetail?.code || `HTTP_${response.status}`;

      throw new ApiError(message, code, response.status, typeof errDetail === 'object' ? errDetail : undefined);
    }

    // If 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err: any) {
    clearTimeout(id);
    if (err.name === 'AbortError') {
      throw new ApiError(`Request timeout after ${timeoutMs}ms`, 'TIMEOUT', 408);
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(err.message || 'Network connection failed', 'NETWORK_ERROR', 0);
  }
}
