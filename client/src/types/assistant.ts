export type AssistantSender = "user" | "assistant";

export interface AssistantScreenContext {
  route?: string;
  title?: string;
  resource?: string;
  filters?: Record<string, string>;
  pagination?: { page?: number; total?: number; totalPages?: number };
  records?: string[];
  selection?: string;
}

export interface AssistantMutation {
  action: string;
  resource: string;
  id: number | null;
}

export interface AssistantChatResponse {
  reply: string;
  isRefusal: boolean;
  refusalReason: string;
  relevantSources: string[];
  suggestedFollowUps: string[];
  toolCalls: string[];
  mutations: AssistantMutation[];
  awaitingConfirmation: boolean;
}

export interface AssistantStatus {
  enabled: boolean;
  model: string;
  name: string;
  institution: string;
  role: string;
  tools: { read: string[]; write: string[] };
}

export interface AssistantMessage {
  id: string;
  sender: AssistantSender;
  text: string;
  createdAt: string;
  isRefusal?: boolean;
  sources?: string[];
  followUps?: string[];
  toolCalls?: string[];
  failed?: boolean;
}
