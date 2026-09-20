import { useEffect, useRef, useState } from "react";
import { useGetIdentity } from "@refinedev/core";
import {
  Bot,
  Loader2,
  RotateCcw,
  Send,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import { Markdown } from "@/components/assistant/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useAssistant } from "@/hooks/use-assistant";
import { cn } from "@/lib/utils";
import type { AssistantMessage } from "@/types/assistant";
import type { User } from "@/types";

const STARTERS_BY_ROLE: Record<string, string[]> = {
  student: [
    "What classes am I enrolled in?",
    "What is on my timetable this week?",
    "I am behind on everything and it is getting to me",
  ],
  lecturer: [
    "Which classes am I teaching this semester?",
    "Show me the roster for my biggest class",
    "Find a free lab for Thursday at 2pm",
  ],
  tutor: [
    "What sessions am I assigned to next week?",
    "Who is enrolled in the class I tutor?",
    "Any unread notifications for me?",
  ],
  admin: [
    "How many active classes are there right now?",
    "Which rooms are free on Monday morning?",
    "List the lecturers in Computer Science",
  ],
  technical_services: [
    "How many rooms and buildings do we have?",
    "Find a computer lab that seats at least 40",
    "Show this week's scheduled sessions",
  ],
};

interface AssistantPanelProps {
  open: boolean;
  onClose: () => void;
}

export function AssistantPanel({ open, onClose }: AssistantPanelProps) {
  const { data: identity } = useGetIdentity<User>();
  const { status, messages, isSending, send, reset } = useAssistant();
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isSending]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    if (open) window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const starters =
    STARTERS_BY_ROLE[status?.role ?? identity?.role ?? "student"] ??
    STARTERS_BY_ROLE.student;

  function submit(text: string) {
    const value = text.trim();
    if (!value || isSending) return;
    void send(value);
    setDraft("");
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-foreground/20 backdrop-blur-[1px] md:hidden"
        onClick={onClose}
        aria-hidden
      />

      <aside
        role="dialog"
        aria-label={`${status?.name ?? "Assistant"} chat`}
        className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-border bg-card shadow-xl sm:w-[420px] lg:w-[460px]"
      >
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Bot className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-semibold">
                  {status?.name ?? "Assistant"}
                </span>
                {status?.enabled && (
                  <Badge variant="secondary" className="gap-1 text-[10px]">
                    <ShieldCheck className="size-3" />
                    Scoped to you
                  </Badge>
                )}
              </div>
              <p className="truncate text-xs text-muted-foreground">
                {status?.institution ?? "Classroom Dashboard"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={reset}
              disabled={messages.length === 0}
              aria-label="Clear conversation"
            >
              <RotateCcw className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="Close assistant"
            >
              <X className="size-4" />
            </Button>
          </div>
        </header>

        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {messages.length === 0 && (
            <EmptyState
              name={status?.name ?? "the assistant"}
              enabled={status?.enabled ?? false}
              starters={starters}
              onPick={submit}
            />
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} onPick={submit} />
          ))}

          {isSending && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" />
              Looking that up in the dashboard...
            </div>
          )}
        </div>

        <form
          className="border-t border-border p-3"
          onSubmit={(event) => {
            event.preventDefault();
            submit(draft);
          }}
        >
          <div className="flex items-end gap-2">
            <Textarea
              ref={inputRef}
              rows={1}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit(draft);
                }
              }}
              placeholder={
                status?.enabled
                  ? "Ask about your classes, timetable or rooms..."
                  : "The assistant is not configured yet"
              }
              disabled={!status?.enabled || isSending}
              className="max-h-32 min-h-9 resize-none"
            />
            <Button
              type="submit"
              size="icon"
              disabled={!status?.enabled || isSending || !draft.trim()}
              aria-label="Send message"
            >
              {isSending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Answers come from live dashboard records you have access to. Check
            anything important before acting on it.
          </p>
        </form>
      </aside>
    </>
  );
}

function EmptyState({
  name,
  enabled,
  starters,
  onPick,
}: {
  name: string;
  enabled: boolean;
  starters: string[];
  onPick: (text: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border bg-muted/40 p-4">
        <div className="mb-1 flex items-center gap-2 text-sm font-medium">
          <Sparkles className="size-4 text-primary" />
          Ask {name} anything about this dashboard
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">
          {enabled
            ? "It reads your classes, timetable, rooms, rosters and notifications directly, and it can see the page you have open. It will ask before changing anything."
            : "Set GEMINI_API_KEY on the server to switch the assistant on."}
        </p>
      </div>

      {enabled && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">
            Try one of these
          </p>
          {starters.map((starter) => (
            <button
              key={starter}
              type="button"
              onClick={() => onPick(starter)}
              className="w-full rounded-md border border-border px-3 py-2 text-left text-sm transition-colors hover:border-primary hover:bg-muted/60"
            >
              {starter}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  message,
  onPick,
}: {
  message: AssistantMessage;
  onPick: (text: string) => void;
}) {
  if (message.sender === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-lg rounded-br-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div
        className={cn(
          "max-w-[95%] rounded-lg rounded-bl-sm border px-3 py-2",
          message.failed
            ? "border-destructive/30 bg-destructive/10 text-destructive"
            : "border-border bg-muted/40 text-foreground",
        )}
      >
        <Markdown text={message.text} />
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {message.sources.map((source) => (
            <Badge key={source} variant="outline" className="text-[10px]">
              {source}
            </Badge>
          ))}
        </div>
      )}

      {message.followUps && message.followUps.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.followUps.map((followUp) => (
            <button
              key={followUp}
              type="button"
              onClick={() => onPick(followUp)}
              className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
            >
              {followUp}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
