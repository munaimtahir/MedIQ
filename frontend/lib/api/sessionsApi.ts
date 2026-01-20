/**
 * Sessions API client for test engine v1
 */

import fetcher from "../fetcher";
import type {
  CreateSessionRequest,
  CreateSessionResponse,
  SessionState,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
  SubmitSessionResponse,
  SessionReview,
} from "../types/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Create a new test session
 */
export async function createSession(payload: CreateSessionRequest): Promise<CreateSessionResponse> {
  return fetcher<CreateSessionResponse>(`${API_BASE}/v1/sessions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Get session state with current question
 */
export async function getSession(sessionId: string): Promise<SessionState> {
  return fetcher<SessionState>(`${API_BASE}/v1/sessions/${sessionId}`, {
    method: "GET",
  });
}

/**
 * Submit or update an answer for a question
 */
export async function submitAnswer(
  sessionId: string,
  payload: SubmitAnswerRequest
): Promise<SubmitAnswerResponse> {
  return fetcher<SubmitAnswerResponse>(`${API_BASE}/v1/sessions/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Submit session and finalize scoring
 */
export async function submitSession(sessionId: string): Promise<SubmitSessionResponse> {
  return fetcher<SubmitSessionResponse>(`${API_BASE}/v1/sessions/${sessionId}/submit`, {
    method: "POST",
  });
}

/**
 * Get session review with frozen content and answers
 */
export async function getSessionReview(sessionId: string): Promise<SessionReview> {
  return fetcher<SessionReview>(`${API_BASE}/v1/sessions/${sessionId}/review`, {
    method: "GET",
  });
}
