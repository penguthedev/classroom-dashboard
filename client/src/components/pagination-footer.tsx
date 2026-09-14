import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PaginationFooterProps {
  currentPage: number;
  pageCount: number;
  total?: number;
  onPageChange: (page: number) => void;
}

export function PaginationFooter({
  currentPage,
  pageCount,
  total,
  onPageChange,
}: PaginationFooterProps) {
  return (
    <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
      <span>
        {total !== undefined ? `${total} total` : ""}
        {pageCount > 0 ? ` · Page ${currentPage} of ${pageCount}` : ""}
      </span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ChevronLeft className="size-4" />
          Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={pageCount === 0 || currentPage >= pageCount}
          onClick={() => onPageChange(currentPage + 1)}
        >
          Next
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
