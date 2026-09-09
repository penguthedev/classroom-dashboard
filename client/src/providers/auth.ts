import type { AuthProvider } from "@refinedev/core";

import { TOKEN_KEY } from "@/constants";
import { http } from "@/lib/http";
import type { AuthResponsePayload, Role, SingleResponse, User } from "@/types";

interface RegisterVariables {
  name: string;
  email: string;
  password: string;
  role: Role;
}

/**
 * Hand-rolled JWT auth provider (per section 7 of the spec — no Better
 * Auth, since it's TS-only on the backend). The token is stored in
 * localStorage and attached to every request by `lib/http.ts`.
 */
export const authProvider: AuthProvider = {
  login: async ({ email, password }) => {
    try {
      const { data } = await http.post<SingleResponse<AuthResponsePayload>>(
        "/auth/login",
        { email, password },
      );
      localStorage.setItem(TOKEN_KEY, data.data.access_token);
      return { success: true, redirectTo: "/" };
    } catch {
      return {
        success: false,
        error: {
          name: "LoginError",
          message: "Invalid email or password",
        },
      };
    }
  },

  register: async (params: RegisterVariables) => {
    try {
      const { data } = await http.post<SingleResponse<AuthResponsePayload>>(
        "/auth/register",
        params,
      );
      localStorage.setItem(TOKEN_KEY, data.data.access_token);
      return { success: true, redirectTo: "/" };
    } catch {
      return {
        success: false,
        error: {
          name: "RegisterError",
          message: "Could not create account. Email may already be in use.",
        },
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
      const { data } = await http.get<SingleResponse<User>>("/auth/me");
      return data.data;
    } catch {
      return null;
    }
  },

  getPermissions: async () => {
    try {
      const { data } = await http.get<SingleResponse<User>>("/auth/me");
      return data.data.role;
    } catch {
      return null;
    }
  },
};
