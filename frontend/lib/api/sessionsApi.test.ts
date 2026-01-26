import { describe, it, expect, vi, beforeEach } from "vitest";
import * as sessionsApi from "./sessionsApi";

// Mock fetcher
vi.mock("../fetcher", () => ({
  default: vi.fn(),
}));

import fetcher from "../fetcher";

describe("sessionsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createSession", () => {
    it("should create a new session", async () => {
      const mockResponse = {
        session_id: "session-123",
        question_ids: ["q1", "q2", "q3"],
      };

      (fetcher as any).mockResolvedValueOnce(mockResponse);

      const result = await sessionsApi.createSession({
        question_ids: ["q1", "q2", "q3"],
        mode: "practice",
      });

      expect(result).toEqual(mockResponse);
      expect(fetcher).toHaveBeenCalledWith(
        expect.stringContaining("/v1/sessions"),
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  describe("getSession", () => {
    it("should fetch session state", async () => {
      const mockSession = {
        session_id: "session-123",
        current_question_id: "q1",
        questions: [],
        answers: {},
      };

      (fetcher as any).mockResolvedValueOnce(mockSession);

      const result = await sessionsApi.getSession("session-123");

      expect(result).toEqual(mockSession);
      expect(fetcher).toHaveBeenCalledWith(
        expect.stringContaining("/v1/sessions/session-123"),
        expect.objectContaining({
          method: "GET",
        })
      );
    });
  });

  describe("submitAnswer", () => {
    it("should submit an answer", async () => {
      const mockResponse = {
        correct: true,
        feedback: "Correct!",
        next_question_id: "q2",
      };

      (fetcher as any).mockResolvedValueOnce(mockResponse);

      const result = await sessionsApi.submitAnswer("session-123", {
        question_id: "q1",
        selected_option_id: "opt1",
      });

      expect(result).toEqual(mockResponse);
      expect(fetcher).toHaveBeenCalledWith(
        expect.stringContaining("/v1/sessions/session-123/answer"),
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });

  describe("submitSession", () => {
    it("should submit a completed session", async () => {
      const mockResponse = {
        session_id: "session-123",
        score: 85,
        total_questions: 10,
        correct_answers: 8,
      };

      (fetcher as any).mockResolvedValueOnce(mockResponse);

      const result = await sessionsApi.submitSession("session-123");

      expect(result).toEqual(mockResponse);
      expect(fetcher).toHaveBeenCalledWith(
        expect.stringContaining("/v1/sessions/session-123/submit"),
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });
});
