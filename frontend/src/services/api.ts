/**
 * Centralized REST API client for SIH26117 Workbench.
 * Encapsulates base URL handling, timeouts, error parsing, request logging,
 * and seamless fallback to realistic mock fixtures for offline air-gap demos.
 */

import {
  MOCK_HEALTH,
  MOCK_SYSTEM_STATUS,
  MOCK_MODEL_TIER,
  MOCK_MODEL_HEALTH,
  MOCK_MODEL_CATALOG,
  MOCK_RAG_STATUS,
  MOCK_RAG_RESULTS,
  MOCK_ROUTING_DECISION,
  MOCK_TASK_RUN_RESPONSE,
  MOCK_DELIVERABLES,
  MOCK_INGESTED_DOCUMENTS,
  MOCK_AUDIT_EVENTS,
  MOCK_AUDIT_VERIFICATION,
  MOCK_NETWORK_REPORT,
  MOCK_SOVEREIGNTY_STATUS,
  MOCK_CORROSION_AUDIT_RESULT,
  MOCK_VALIDATION_REPORT,
} from './mockData';

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

/**
 * Resolves fallback mock data for read-only system telemetry when backend is not running.
 * CRITICAL RULE: Operational endpoints (/workflows/*, /agent/*, /files/*, /deliverables)
 * MUST NEVER silently return mock calculation data. They must fail explicitly with ApiError.
 */
function getMockFallback<T>(endpoint: string, options: RequestInit = {}): T | null {
  const cleanEndpoint = endpoint.replace(/^\/api\/v1/, '').split('?')[0];

  // OPERATIONAL ENDPOINTS: strictly fail closed, NO silent fallback!
  if (
    cleanEndpoint.startsWith('/workflows') ||
    cleanEndpoint.startsWith('/agent') ||
    cleanEndpoint.startsWith('/files') ||
    cleanEndpoint.startsWith('/deliverables')
  ) {
    return null;
  }

  if (cleanEndpoint === '/health' || cleanEndpoint.endsWith('/health')) {
    if (cleanEndpoint.includes('/models/')) return MOCK_MODEL_HEALTH as unknown as T;
    return MOCK_HEALTH as unknown as T;
  }

  if (cleanEndpoint === '/system/status') {
    return MOCK_SYSTEM_STATUS as unknown as T;
  }

  if (cleanEndpoint === '/models/tier') {
    return MOCK_MODEL_TIER as unknown as T;
  }

  if (cleanEndpoint === '/models') {
    return MOCK_MODEL_CATALOG as unknown as T;
  }

  if (cleanEndpoint === '/rag/status') {
    return MOCK_RAG_STATUS as unknown as T;
  }

  if (cleanEndpoint === '/rag/query') {
    return MOCK_RAG_RESULTS as unknown as T;
  }

  if (cleanEndpoint === '/router/route') {
    return MOCK_ROUTING_DECISION as unknown as T;
  }

  if (cleanEndpoint === '/audit/events') {
    return {
      items: MOCK_AUDIT_EVENTS,
      total: MOCK_AUDIT_EVENTS.length,
      limit: 50,
      offset: 0,
    } as unknown as T;
  }

  if (cleanEndpoint.startsWith('/audit/events/')) {
    const id = cleanEndpoint.split('/').pop();
    const ev = MOCK_AUDIT_EVENTS.find(e => e.event_id === id) || MOCK_AUDIT_EVENTS[0];
    return { event: ev } as unknown as T;
  }

  if (cleanEndpoint === '/audit/integrity' || cleanEndpoint === '/audit/verify') {
    return { verification: MOCK_AUDIT_VERIFICATION } as unknown as T;
  }

  if (cleanEndpoint === '/audit/network') {
    return { report: MOCK_NETWORK_REPORT } as unknown as T;
  }

  if (cleanEndpoint === '/audit/sovereignty') {
    return { sovereignty: MOCK_SOVEREIGNTY_STATUS } as unknown as T;
  }

  return null;
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs = 15000
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
      // If server returned 404 or 502/503/500, try mock fallback
      const fallback = getMockFallback<T>(endpoint, options);
      if (fallback !== null) {
        console.info(`[Sovereign Fallback] Server responded with HTTP ${response.status} for ${endpoint}. Used local offline fixture.`);
        return fallback;
      }

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

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  } catch (err: any) {
    clearTimeout(id);

    // If fetch failed due to network error or abort, return mock fallback
    const fallback = getMockFallback<T>(endpoint, options);
    if (fallback !== null) {
      console.info(`[Sovereign Fallback] Offline mode activated for ${endpoint} (${err.message || 'Fetch failed'}).`);
      return fallback;
    }

    if (err.name === 'AbortError') {
      throw new ApiError(`Request timeout after ${timeoutMs}ms`, 'TIMEOUT', 408);
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(err.message || 'Network connection failed', 'NETWORK_ERROR', 0);
  }
}
