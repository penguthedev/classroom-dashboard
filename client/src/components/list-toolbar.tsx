import type { PropsWithChildren } from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

interface ListToolbarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  placeholder?: string;
}

export function ListToolbar({
  searchValue,
  onSearchChange,
  placeholder = "Search...",
  children,
}: PropsWithChildren<ListToolbarProps>) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="relative w-full max-w-xs">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={placeholder}
          className="pl-8"
        />
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}
