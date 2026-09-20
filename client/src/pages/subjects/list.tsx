import { useList, useTable } from "@refinedev/core";

import { ListToolbar } from "@/components/list-toolbar";
import { PaginationFooter } from "@/components/pagination-footer";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RESOURCES } from "@/constants";
import type { Department, Subject } from "@/types";

export function SubjectsListPage() {
  const {
    result,
    tableQuery: { isLoading },
    currentPage,
    setCurrentPage,
    pageCount,
    filters,
    setFilters,
  } = useTable<Subject>({
    resource: RESOURCES.subjects,
    pagination: { pageSize: 10 },
  });

  // Powers the department filter dropdown — small list, first page is enough.
  const { result: departmentsResult } = useList<Department>({
    resource: RESOURCES.departments,
    pagination: { pageSize: 100 },
  });

  const searchValue =
    (filters.find((f) => "field" in f && f.field === "search")?.value as
      | string
      | undefined) ?? "";
  const departmentValue =
    (filters.find((f) => "field" in f && f.field === "department")?.value as
      | string
      | undefined) ?? "";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Subjects</h1>
        <p className="text-sm text-muted-foreground">
          Subjects offered across all departments.
        </p>
      </div>

      <ListToolbar
        searchValue={searchValue}
        onSearchChange={(value) =>
          setFilters(
            [{ field: "search", operator: "eq", value }],
            "merge",
          )
        }
        placeholder="Search subjects..."
      >
        <Select
          value={departmentValue}
          onChange={(e) =>
            setFilters(
              [
                {
                  field: "department",
                  operator: "eq",
                  value: e.target.value,
                },
              ],
              "merge",
            )
          }
          className="w-48"
        >
          <option value="">All departments</option>
          {departmentsResult?.data.map((department) => (
            <option key={department.id} value={department.name}>
              {department.name}
            </option>
          ))}
        </Select>
      </ListToolbar>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Department</TableHead>
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
                  No subjects found.
                </TableCell>
              </TableRow>
            ) : (
              result.data.map((subject) => (
                <TableRow key={subject.id}>
                  <TableCell className="font-mono text-xs">
                    {subject.code}
                  </TableCell>
                  <TableCell className="font-medium">{subject.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {subject.department.name}
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
