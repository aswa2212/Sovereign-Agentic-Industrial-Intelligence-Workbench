/**
 * Service methods for interacting with Phase 7 Agent Orchestrator & Phase 3 Router.
 */

import { request } from './api';
import { AgentRunRequest, AgentRunResponse, AgentTaskStatusResponse } from '../types/agent';
import { RouteResponse } from '../types/api';

export const agentService = {
  /**
   * Submit an autonomous task to the agent orchestrator.
   */
  async runTask(task: string, maxSteps = 8): Promise<AgentRunResponse> {
    const payload: AgentRunRequest = {
      task: task.trim(),
      max_steps: maxSteps,
    };
    return request<AgentRunResponse>('/agent/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }, 60000); // 60s timeout for agent reasoning
  },

  /**
   * Poll intermediate or final execution trace for a given task ID.
   */
  async getTaskStatus(taskId: string): Promise<AgentTaskStatusResponse> {
    return request<AgentTaskStatusResponse>(`/agent/${taskId}`, {
      method: 'GET',
    });
  },

  /**
   * Preview Task Router classification before running.
   */
  async routeTask(task: string): Promise<RouteResponse> {
    return request<RouteResponse>('/router/route', {
      method: 'POST',
      body: JSON.stringify({ task: task.trim() }),
    });
  },
};
