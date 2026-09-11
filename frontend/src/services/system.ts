/**
 * System and Health monitoring service methods.
 */

import { request } from './api';
import {
  HealthResponse,
  SystemStatusResponse,
  BackendHealthResponse,
  TierConfigResponse,
  ModelListResponse,
  RAGStatusResponse,
  RAGQueryResponse,
} from '../types/api';

export const systemService = {
  /**
   * Root health probe checking air-gap assertion and gateway status.
   */
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
  },

  /**
   * Diagnostic system status endpoint.
   */
  async getStatus(): Promise<SystemStatusResponse> {
    return request<SystemStatusResponse>('/system/status');
  },

  /**
   * Active hardware tier configuration and model role mappings.
   */
  async getModelTier(): Promise<TierConfigResponse> {
    return request<TierConfigResponse>('/models/tier');
  },

  /**
   * Model backend liveness health probe.
   */
  async getModelHealth(): Promise<BackendHealthResponse> {
    return request<BackendHealthResponse>('/models/health');
  },

  /**
   * Discovered models currently resident or available in local inference provider.
   */
  async getModelList(): Promise<ModelListResponse> {
    return request<ModelListResponse>('/models');
  },

  /**
   * Diagnostic metadata on RAG vector store and embeddings.
   */
  async getRAGStatus(): Promise<RAGStatusResponse> {
    return request<RAGStatusResponse>('/rag/status');
  },

  /**
   * Query the sovereign vector store directly for evidence chunks.
   */
  async queryRAG(query: string, topK = 3, threshold = 0.65): Promise<RAGQueryResponse> {
    return request<RAGQueryResponse>('/rag/query', {
      method: 'POST',
      body: JSON.stringify({
        query: query.trim(),
        top_k: topK,
        similarity_threshold: threshold,
      }),
    });
  },
};
