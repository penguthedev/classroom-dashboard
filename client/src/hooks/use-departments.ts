import { useEffect, useState } from "react";

import { http } from "@/lib/http";
import type { Department } from "@/types";

/**
 * Departments are needed on the registration wizard (brief sections 3-6),
 * which runs before the user has a token, so this hits the public
 * GET /api/departments endpoint directly rather than going through the
 * authenticated Refine data provider.
 */
export function useDepartments() {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    http
      .get<Department[]>("/departments")
      .then(({ data }) => {
        if (!cancelled) setDepartments(data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load departments. Please refresh and try again.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { departments, isLoading, error };
}
