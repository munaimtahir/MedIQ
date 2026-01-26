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
  SessionStateThin,
  QuestionWithAnswerState,
  PrefetchQuestionsResponse,
  AnswerSubmitThinRequest,
  AnswerSubmitThinResponse,
  SessionSubmitThinResponse,
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
 * Get session state with current question (legacy, full payload)
 */
export async function getSession(sessionId: string): Promise<SessionState> {
  return fetcher<SessionState>(`${API_BASE}/v1/sessions/${sessionId}`, {
    method: "GET",
  });
}

/**
 * Get thin session state (metadata only, optimized for polling)
 */
export async function getSessionStateThin(sessionId: string): Promise<SessionStateThin> {
  return fetcher<SessionStateThin>(`${API_BASE}/v1/sessions/${sessionId}/state`, {
    method: "GET",
  });
}

/**
 * Get single question by index (thin payload, optimized for prefetching)
 */
export async function getSessionQuestion(
  sessionId: string,
  index: number,
): Promise<QuestionWithAnswerState> {
  return fetcher<QuestionWithAnswerState>(
    `${API_BASE}/v1/sessions/${sessionId}/question?index=${index}`,
    {
      method: "GET",
    },
  );
}

/**
 * Prefetch multiple questions (optimized for instant navigation)
 */
export async function prefetchQuestions(
  sessionId: string,
  fromIndex: number,
  count: number,
): Promise<PrefetchQuestionsResponse> {
  return fetcher<PrefetchQuestionsResponse>(
    `${API_BASE}/v1/sessions/${sessionId}/questions/prefetch?from=${fromIndex}&count=${count}`,
    {
      method: "GET",
    },
  );
}

/**
 * Submit or update an answer for a question (legacy)
 */
export async function submitAnswer(
  sessionId: string,
  payload: SubmitAnswerRequest,
): Promise<SubmitAnswerResponse> {
  return fetcher<SubmitAnswerResponse>(`${API_BASE}/v1/sessions/${sessionId}/answer`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Submit answer (thin endpoint, idempotent)
 */
export async function submitAnswerThin(
  sessionId: string,
  payload: AnswerSubmitThinRequest,
): Promise<AnswerSubmitThinResponse> {
  return fetcher<AnswerSubmitThinResponse>(`${API_BASE}/v1/sessions/${sessionId}/answer-thin`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Submit session and finalize scoring (legacy)
 */
export async function submitSession(sessionId: string): Promise<SubmitSessionResponse> {
  return fetcher<SubmitSessionResponse>(`${API_BASE}/v1/sessions/${sessionId}/submit`, {
    method: "POST",
  });
}

/**
 * Submit session (thin endpoint)
 */
export async function submitSessionThin(sessionId: string): Promise<SessionSubmitThinResponse> {
  return fetcher<SessionSubmitThinResponse>(`${API_BASE}/v1/sessions/${sessionId}/submit-thin`, {
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
