import { Link } from "react-router-dom";
import { useTable } from "@refinedev/core";
import { Plus } from "lucide-react";

import { ListToolbar } from "@/components/list-toolbar";
import { PaginationFooter } from "@/components/pagination-footer";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RESOURCES } from "@/constants";
import type { Class } from "@/types";

export function ClassesListPage() {
  const {
    result,
    tableQuery: { isLoading },
    currentPage,
    setCurrentPage,
    pageCount,
    filters,
    setFilters,
  } = useTable<Class>({
    resource: RESOURCES.classes,
    pagination: { pageSize: 10 },
  });

  const searchValue =
    (filters.find((f) => "field" in f && f.field === "search")?.value as
      | string
      | undefined) ?? "";

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Classes</h1>
          <p className="text-sm text-muted-foreground">
            Every class section across all subjects.
          </p>
        </div>
        <Link to="/classes/create" className={buttonVariants({})}>
          <Plus />
          New class
        </Link>
      </div>

      <ListToolbar
        searchValue={searchValue}
        onSearchChange={(value) =>
          setFilters([{ field: "search", operator: "eq", value }])
        }
        placeholder="Search classes..."
      />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Subject</TableHead>
              <TableHead>Teacher</TableHead>
              <TableHead>Capacity</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  Loading...
                </TableCell>
              </TableRow>
            ) : result.data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  No classes found.
                </TableCell>
              </TableRow>
            ) : (
              result.data.map((klass) => (
                <TableRow key={klass.id}>
                  <TableCell className="font-medium">
                    <Link
                      to={`/classes/${klass.id}`}
                      className="hover:underline"
                    >
                      {klass.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {klass.subject.name}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {klass.lecturer.full_name}
                  </TableCell>
                  <TableCell>{klass.capacity}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        klass.status === "active" ? "default" : "secondary"
                      }
                      className="capitalize"
                    >
                      {klass.status}
                    </Badge>
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
