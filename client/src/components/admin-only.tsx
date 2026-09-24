import type { PropsWithChildren } from "react";
import { useGetIdentity } from "@refinedev/core";
import { ShieldAlert } from "lucide-react";

import type { User } from "@/types";

/** Renders its children only for signed-in admins. The API enforces the same
 * rule, this just avoids showing a page full of 403 errors to everyone else. */
export function AdminOnly({ children }: PropsWithChildren) {
  const { data: identity, isLoading } = useGetIdentity<User>();

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading...</p>;
  }

  if (identity?.role !== "admin") {
    return (
      <div className="mx-auto mt-16 max-w-md rounded-xl border bg-card p-8 text-center shadow-sm">
        <ShieldAlert className="mx-auto mb-3 size-8 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Admins only</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          You need an admin account to open this page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
