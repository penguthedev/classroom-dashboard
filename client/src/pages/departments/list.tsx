import { useTable } from "@refinedev/core";

import { ListToolbar } from "@/components/list-toolbar";
import { PaginationFooter } from "@/components/pagination-footer";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RESOURCES } from "@/constants";
import type { Department } from "@/types";

export function DepartmentsListPage() {
  const {
    result,
    tableQuery: { isLoading },
    currentPage,
    setCurrentPage,
    pageCount,
    filters,
    setFilters,
  } = useTable<Department>({
    resource: RESOURCES.departments,
    pagination: { pageSize: 10 },
  });

  const searchValue =
    (filters.find((f) => "field" in f && f.field === "search")?.value as
      | string
      | undefined) ?? "";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Departments</h1>
        <p className="text-sm text-muted-foreground">
          All academic departments.
        </p>
      </div>

      <ListToolbar
        searchValue={searchValue}
        onSearchChange={(value) =>
          setFilters([{ field: "search", operator: "eq", value }])
        }
        placeholder="Search departments..."
      />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={3} className="py-8 text-center text-muted-foreground">
                  Loading...
                </TableCell>
              </TableRow>
            ) : result.data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="py-8 text-center text-muted-foreground">
                  No departments found.
                </TableCell>
              </TableRow>
            ) : (
              result.data.map((department) => (
                <TableRow key={department.id}>
                  <TableCell className="font-mono text-xs">
                    {department.code}
                  </TableCell>
                  <TableCell className="font-medium">
                    {department.name}
                  </TableCell>
                  <TableCell className="max-w-md truncate text-muted-foreground">
                    {department.description ?? "—"}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <PaginationFooter
        currentPage={currentPage}
        pageCount={pageCount}
        total={result.total}
        onPageChange={setCurrentPage}
      />
    </div>
  );
}
