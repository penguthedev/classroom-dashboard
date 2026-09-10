import type { AuthProvider } from "@refinedev/core";
import type { AxiosError } from "axios";

import { TOKEN_KEY } from "@/constants";
import { http } from "@/lib/http";
import type { LockoutDetail, Role, TokenResponsePayload, User } from "@/types";

interface LoginVariables {
  identifier: string;
  password: string;
}

interface RegisterVariables {
  role: Role;
  formData: FormData;
}

const REGISTER_ENDPOINTS: Record<Role, string> = {
  student: "/auth/register/student",
  lecturer: "/auth/register/lecturer",
  tutor: "/auth/register/tutor",
  admin: "/auth/register/admin",
  technical_services: "/auth/register/technical-services",
};

function extractDetailMessage(error: unknown): string {
  const axiosErr = error as AxiosError<{ detail?: unknown }>;
  const detail = axiosErr.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in (detail as any)) {
    return String((detail as any).message);
  }
  if (Array.isArray(detail) && detail.length > 0 && typeof detail[0]?.msg === "string") {
    return detail[0].msg as string;
  }
  return "Something went wrong. Please try again.";
}

/**
 * Hand-rolled JWT auth provider talking to the FastAPI backend directly
 * (see server/app/api/auth.py). Token lives in localStorage and is attached
 * to every request by lib/http.ts.
 */
export const authProvider: AuthProvider = {
  login: async ({ identifier, password }: LoginVariables) => {
    try {
      const { data } = await http.post<TokenResponsePayload>("/auth/login", {
        identifier,
        password,
      });
      localStorage.setItem(TOKEN_KEY, data.access_token);
      return { success: true, redirectTo: "/" };
    } catch (error) {
      const axiosErr = error as AxiosError<{ detail?: LockoutDetail | string }>;
      if (axiosErr.response?.status === 423) {
        const detail = axiosErr.response.data?.detail as LockoutDetail;
        return {
          success: false,
          error: {
            name: "LockedError",
            message: detail?.message ?? "Too many failed login attempts.",
            // Extra field consumed by LoginPage for the countdown; not part
            // of Refine's typed error shape, so it's read back with a cast.
            ...( { retryAfterSeconds: detail?.retry_after_seconds } as any),
          },
        };
      }
      return {
        success: false,
        error: { name: "LoginError", message: extractDetailMessage(error) },
      };
    }
  },

  register: async ({ role, formData }: RegisterVariables) => {
    try {
      const { data } = await http.post<TokenResponsePayload>(
        REGISTER_ENDPOINTS[role],
        formData,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      localStorage.setItem(TOKEN_KEY, data.access_token);
      return { success: true, redirectTo: "/" };
    } catch (error) {
      return {
        success: false,
        error: { name: "RegisterError", message: extractDetailMessage(error) },
      };
    }
  },

  logout: async () => {
    localStorage.removeItem(TOKEN_KEY);
    return { success: true, redirectTo: "/login" };
  },

  check: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      return { authenticated: false, redirectTo: "/login" };
    }
    try {
      await http.get("/auth/me");
      return { authenticated: true };
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      return { authenticated: false, redirectTo: "/login" };
    }
  },

  onError: async (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      return { logout: true, redirectTo: "/login" };
    }
    return {};
  },

  getIdentity: async () => {
    try {
      const { data } = await http.get<User>("/auth/me");
      return data;
    } catch {
      return null;
    }
  },

  getPermissions: async () => {
    try {
      const { data } = await http.get<User>("/auth/me");
      return data.role;
    } catch {
      return null;
    }
  },
};
