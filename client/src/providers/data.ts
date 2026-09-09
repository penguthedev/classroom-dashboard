import type { DataProvider } from "@refinedev/core";

import { API_BASE_URL } from "@/constants";
import { http } from "@/lib/http";
import type { ListResponse, SingleResponse } from "@/types";

/**
 * Refine data provider wired to the FastAPI backend described in section 5
 * of the project spec:
 *
 *   GET    /api/{resource}?page=&limit=&search=&department=
 *          -> { data: [...], pagination: { page, limit, total, totalPages } }
 *   GET    /api/{resource}/{id}          -> { data: {...} }
 *   POST   /api/{resource}               -> 201 { data: {...} }
 *   PATCH  /api/{resource}/{id}          -> 200 { data: {...} }
 *   DELETE /api/{resource}/{id}          -> 204
 *
 * Filters map 1:1 onto extra query params (`search`, `department`,
 * `subject`, `teacher`) rather than Refine's generic filter DSL, because
 * that's what the backend actually accepts.
 */
export const dataProvider: DataProvider = {
  getApiUrl: () => API_BASE_URL,

  getList: async ({ resource, pagination, filters, meta }) => {
    const params: Record<string, string | number> = {
      page: pagination?.currentPage ?? 1,
      limit: pagination?.pageSize ?? 10,
    };

    for (const filter of filters ?? []) {
      if ("field" in filter && filter.value !== undefined && filter.value !== "") {
        params[filter.field] = filter.value;
      }
    }

    Object.assign(params, meta?.query ?? {});

    const { data } = await http.get<ListResponse<unknown>>(`/${resource}`, {
      params,
    });

    return {
      data: data.data as never[],
      total: data.pagination.total,
    };
  },

  getOne: async ({ resource, id }) => {
    const { data } = await http.get<SingleResponse<unknown>>(
      `/${resource}/${id}`,
    );
    return { data: data.data as never };
  },

  create: async ({ resource, variables }) => {
    const { data } = await http.post<SingleResponse<unknown>>(
      `/${resource}`,
      variables,
    );
    return { data: data.data as never };
  },

  update: async ({ resource, id, variables }) => {
    const { data } = await http.patch<SingleResponse<unknown>>(
      `/${resource}/${id}`,
      variables,
    );
    return { data: data.data as never };
  },

  deleteOne: async ({ resource, id }) => {
    await http.delete(`/${resource}/${id}`);
    return { data: { id } as never };
  },

  getMany: async ({ resource, ids }) => {
    const results = await Promise.all(
      ids.map((id) =>
        http.get<SingleResponse<unknown>>(`/${resource}/${id}`),
      ),
    );
    return { data: results.map((r) => r.data.data) as never[] };
  },
};
