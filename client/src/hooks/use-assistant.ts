import { useCallback, useEffect, useRef, useState } from "react";
import { useInvalidate } from "@refinedev/core";
import type { AxiosError } from "axios";

import { captureScreenContext } from "@/lib/assistant-context";
import { http } from "@/lib/http";
import type {
  AssistantChatResponse,
  AssistantMessage,
  AssistantStatus,
} from "@/types/assistant";

const HISTORY_LIMIT = 12;

function nextId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function errorMessage(error: unknown): string {
  const axiosErr = error as AxiosError<{ detail?: unknown }>;
  const detail = axiosErr.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (axiosErr.response?.status === 503) {
    return "The assistant is not configured on this server yet.";
  }
  return "I could not reach the assistant. Please try again in a moment.";
}

export function useAssistant() {
  const invalidate = useInvalidate();
  const [status, setStatus] = useState<AssistantStatus | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const messagesRef = useRef<AssistantMessage[]>([]);

  messagesRef.current = messages;

  useEffect(() => {
    let cancelled = false;
    http
      .get<AssistantStatus>("/assistant/status")
      .then(({ data }) => {
        if (!cancelled) setStatus(data);
      })
      .catch(() => {
        if (!cancelled) setStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      const outgoing: AssistantMessage = {
        id: nextId(),
        sender: "user",
        text: trimmed,
        createdAt: new Date().toISOString(),
      };

      const history = messagesRef.current
        .filter((message) => !message.failed)
        .slice(-HISTORY_LIMIT)
        .map((message) => ({ sender: message.sender, text: message.text }));

      setMessages((prev) => [...prev, outgoing]);
      setIsSending(true);

      try {
        const { data } = await http.post<AssistantChatResponse>(
          "/assistant/chat",
          {
            message: trimmed,
            history,
            context: captureScreenContext(),
          },
        );

        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            sender: "assistant",
            text: data.reply,
            createdAt: new Date().toISOString(),
            isRefusal: data.isRefusal,
            sources: data.relevantSources,
            followUps: data.suggestedFollowUps,
            toolCalls: data.toolCalls,
          },
        ]);

        const touched = new Set(data.mutations.map((m) => m.resource));
        touched.forEach((resource) => {
          invalidate({ resource, invalidates: ["list", "many", "detail"] });
        });
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            sender: "assistant",
            text: errorMessage(error),
            createdAt: new Date().toISOString(),
            failed: true,
          },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [invalidate, isSending],
  );

  const reset = useCallback(() => setMessages([]), []);

  return { status, messages, isSending, send, reset };
}
