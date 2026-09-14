import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Minimal native <select>, styled to match the rest of the inputs. Swap
 * for @radix-ui/react-select + shadcn's Select if you need multi-select,
 * search, or richer option content later.
 */
function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export { Select };
