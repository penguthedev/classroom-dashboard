import { Fragment, useState } from "react";
import { useTable } from "@refinedev/core";
import type { AxiosError } from "axios";
import { Check, ChevronDown, ChevronRight, FileText, Loader2, X } from "lucide-react";

import { AdminOnly } from "@/components/admin-only";
import { ListToolbar } from "@/components/list-toolbar";
import { PaginationFooter } from "@/components/pagination-footer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ROLES, RESOURCES } from "@/constants";
import { notifyApprovalsChanged } from "@/hooks/use-pending-approvals";
import { http } from "@/lib/http";
import { ROLE_LABELS, type User } from "@/types";

type StatusFilter = "false" | "true" | "";

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "false", label: "Pending approval" },
  { value: "true", label: "Approved" },
  { value: "", label: "All accounts" },
];

function errorMessage(error: unknown): string {
  const detail = (error as AxiosError<{ detail?: unknown }>).response?.data?.detail;
  return typeof detail === "string" ? detail : "Something went wrong. Please try again.";
}

function humanize(key: string) {
  return key.replace(/_url$/, "").replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function ApprovalsPage() {
  return (
    <AdminOnly>
      <ApprovalsTable />
    </AdminOnly>
  );
}

function ApprovalsTable() {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const {
    result,
    tableQuery: { isLoading, refetch },
    currentPage,
    setCurrentPage,
    pageCount,
    filters,
    setFilters,
  } = useTable<User>({
    resource: RESOURCES.users,
    pagination: { pageSize: 10 },
    filters: { initial: [{ field: "is_approved", operator: "eq", value: "false" }] },
  });

  const filterValue = (field: string) =>
    String(filters.find((f) => "field" in f && f.field === field)?.value ?? "");

  const setFilter = (field: string, value: string) => {
    setCurrentPage(1);
    setFilters([{ field, operator: "eq", value }]);
  };

  async function act(user: User, action: "approve" | "reject") {
    if (
      action === "reject" &&
      !window.confirm(
        `Reject ${user.full_name}'s registration? Their account will be removed and they'll need to register again.`,
      )
    ) {
      return;
    }
    setBusyId(user.id);
    setMessage(null);
    try {
      await http.post(`/users/${user.id}/${action}`);
      setMessage({
        kind: "ok",
        text:
          action === "approve"
            ? `${user.full_name} is approved and can now sign in.`
            : `${user.full_name}'s registration was rejected.`,
      });
      notifyApprovalsChanged();
      await refetch();
    } catch (error) {
      setMessage({ kind: "error", text: errorMessage(error) });
    } finally {
      setBusyId(null);
    }
  }

  const status = filterValue("is_approved") as StatusFilter;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Account approvals</h1>
        <p className="text-sm text-muted-foreground">
          New students, lecturers, tutors and technical staff can't sign in until you approve them.
        </p>
      </div>

      <ListToolbar
        searchValue={filterValue("search")}
        onSearchChange={(value) => setFilter("search", value)}
        placeholder="Search name, email or username..."
      >
        <Select
          aria-label="Status"
          className="w-44"
          value={status}
          onChange={(e) => setFilter("is_approved", e.target.value)}
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.label} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          aria-label="Role"
          className="w-44"
          value={filterValue("role")}
          onChange={(e) => setFilter("role", e.target.value)}
        >
          <option value="">All roles</option>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </Select>
      </ListToolbar>

      {message && (
        <div
          className={
            "mb-4 rounded-md border px-3 py-2 text-sm " +
            (message.kind === "ok"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
              : "border-destructive/30 bg-destructive/10 text-destructive")
          }
        >
          {message.text}
        </div>
      )}

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-8" />
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>ID</TableHead>
              <TableHead>Registered</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  Loading...
                </TableCell>
              </TableRow>
            ) : result.data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  {status === "false" ? "No accounts are waiting for approval." : "No accounts found."}
                </TableCell>
              </TableRow>
            ) : (
              result.data.map((user) => {
                const expanded = expandedId === user.id;
                const busy = busyId === user.id;
                return (
                  <Fragment key={user.id}>
                    <TableRow>
                      <TableCell>
                        <button
                          type="button"
                          onClick={() => setExpandedId(expanded ? null : user.id)}
                          className="text-muted-foreground hover:text-foreground"
                          aria-label={expanded ? "Hide details" : "Show details"}
                        >
                          {expanded ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                        </button>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">{user.full_name}</div>
                        <div className="text-xs text-muted-foreground">{user.email}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{ROLE_LABELS[user.role]}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{user.id_code ?? "—"}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(user.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {user.is_approved ? (
                          <Badge variant="secondary">Approved</Badge>
                        ) : (
                          <Badge className="bg-amber-500 text-white">Pending</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {user.is_approved ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : (
                          <div className="flex justify-end gap-2">
                            <Button size="sm" disabled={busy} onClick={() => act(user, "approve")}>
                              {busy ? <Loader2 className="animate-spin" /> : <Check />}
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busy}
                              onClick={() => act(user, "reject")}
                            >
                              <X />
                              Reject
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                    {expanded && (
                      <TableRow className="bg-muted/30 hover:bg-muted/30">
                        <TableCell />
                        <TableCell colSpan={6}>
                          <UserDetails user={user} />
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })
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

function UserDetails({ user }: { user: User }) {
  const profile = (user.profile ?? {}) as Record<string, unknown>;
  const documents = Object.entries(profile).filter(
    ([key, value]) => key.endsWith("_url") && typeof value === "string" && value,
  ) as [string, string][];
  const fields: [string, unknown][] = [
    ["Username", user.username],
    ["Phone", user.phone_number],
    ["Address", user.address],
    ["Emergency contact", [user.emergency_contact_name, user.emergency_contact_phone].filter(Boolean).join(" · ")],
    ...Object.entries(profile).filter(
      ([key, value]) => !key.endsWith("_url") && !key.endsWith("_id") && value !== null && value !== "",
    ).map(([key, value]) => [humanize(key), value] as [string, unknown]),
  ];

  return (
    <div className="grid gap-4 py-2 sm:grid-cols-2">
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
        {fields
          .filter(([, value]) => value !== null && value !== undefined && value !== "")
          .map(([label, value]) => (
            <Fragment key={label}>
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="break-words">{String(value).replace(/_/g, " ")}</dd>
            </Fragment>
          ))}
      </dl>
      <div>
        <p className="mb-1 text-sm text-muted-foreground">Uploaded documents</p>
        {documents.length === 0 ? (
          <p className="text-sm">None uploaded</p>
        ) : (
          <ul className="space-y-1">
            {documents.map(([key, url]) => (
              <li key={key}>
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-primary underline-offset-4 hover:underline"
                >
                  <FileText className="size-4" />
                  {humanize(key)}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
