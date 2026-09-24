import { useCallback, useEffect, useState } from "react";

import { http } from "@/lib/http";

const CHANGED_EVENT = "uniboard:approvals-changed";

/** Tell every mounted usePendingApprovals() to refresh (e.g. after approving). */
export function notifyApprovalsChanged() {
  window.dispatchEvent(new Event(CHANGED_EVENT));
}

/**
 * Number of accounts waiting for admin approval. Only fetches when `enabled`
 * (i.e. the viewer is an admin) and refreshes every 30s plus whenever an
 * approval/rejection happens elsewhere in the app.
 */
export function usePendingApprovals(enabled: boolean) {
  const [count, setCount] = useState<number | null>(null);

  const refresh = useCallback(() => {
    if (!enabled) return;
    http
      .get<{ data: { pending: number } }>("/users/pending-count")
      .then(({ data }) => setCount(data.data.pending))
      .catch(() => setCount(null));
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    const timer = window.setInterval(refresh, 30_000);
    window.addEventListener(CHANGED_EVENT, refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener(CHANGED_EVENT, refresh);
    };
  }, [enabled, refresh]);

  return enabled ? count : null;
}
