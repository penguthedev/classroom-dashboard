import type { AssistantScreenContext } from "@/types/assistant";

const MAX_RECORDS = 25;
const MAX_CELL_LENGTH = 60;
const MAX_SELECTION_LENGTH = 1500;

const RESOURCE_BY_SEGMENT: Record<string, string> = {
  departments: "departments",
  subjects: "subjects",
  classes: "classes",
  users: "users",
  enrollments: "enrollments",
};

function squash(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function readResource(pathname: string): string | undefined {
  const segment = pathname.split("/").filter(Boolean)[0];
  if (!segment) return "dashboard";
  return RESOURCE_BY_SEGMENT[segment];
}

function readTitle(root: ParentNode): string | undefined {
  const heading = root.querySelector("h1");
  const text = squash(heading?.textContent);
  return text || squash(document.title) || undefined;
}

function readFilters(search: string): Record<string, string> | undefined {
  const params = new URLSearchParams(search);
  const fields: Record<string, string> = {};
  const values: Record<string, string> = {};
  const filters: Record<string, string> = {};

  params.forEach((value, key) => {
    const fieldMatch = key.match(/^filters\[(\d+)\]\[field\]$/);
    if (fieldMatch) {
      fields[fieldMatch[1]] = value;
      return;
    }
    const valueMatch = key.match(/^filters\[(\d+)\]\[value\]$/);
    if (valueMatch) {
      values[valueMatch[1]] = value;
      return;
    }
    if (!key.startsWith("filters[") && value) {
      filters[key] = value;
    }
  });

  Object.entries(fields).forEach(([index, field]) => {
    if (values[index]) filters[field] = values[index];
  });

  return Object.keys(filters).length > 0 ? filters : undefined;
}

function readTableRecords(root: ParentNode): string[] | undefined {
  const table = root.querySelector("table");
  if (!table) return undefined;

  const headers = Array.from(table.querySelectorAll("thead th")).map((cell) =>
    squash(cell.textContent),
  );

  const rows = Array.from(table.querySelectorAll("tbody tr")).slice(0, MAX_RECORDS);
  const records = rows
    .map((row) => {
      const cells = Array.from(row.querySelectorAll("td")).map((cell) =>
        truncate(squash(cell.textContent), MAX_CELL_LENGTH),
      );
      if (cells.length === 0) return "";
      if (cells.length === 1 && !cells[0]) return "";
      return cells
        .map((cell, index) =>
          headers[index] ? `${headers[index]}: ${cell}` : cell,
        )
        .join(" | ");
    })
    .filter(Boolean);

  return records.length > 0 ? records : undefined;
}

function readDetail(root: ParentNode): string | undefined {
  const list = root.querySelector("dl");
  if (!list) return undefined;

  const parts: string[] = [];
  const terms = Array.from(list.querySelectorAll("dt"));
  terms.forEach((term) => {
    const label = squash(term.textContent);
    const values: string[] = [];
    let sibling = term.nextElementSibling;
    while (sibling && sibling.tagName === "DD") {
      const value = squash(sibling.textContent);
      if (value) values.push(value);
      sibling = sibling.nextElementSibling;
    }
    if (label && values.length > 0) parts.push(`${label}: ${values.join(" / ")}`);
  });

  if (parts.length === 0) return undefined;
  return truncate(parts.join(" | "), MAX_SELECTION_LENGTH);
}

function readPagination(root: ParentNode): AssistantScreenContext["pagination"] {
  const text = squash(root.querySelector("main")?.textContent ?? "");
  const totalMatch = text.match(/(\d+)\s+(?:results?|rows?|items?|total)/i);
  const pageMatch = text.match(/page\s+(\d+)\s+of\s+(\d+)/i);

  if (!totalMatch && !pageMatch) return undefined;
  return {
    page: pageMatch ? Number(pageMatch[1]) : undefined,
    totalPages: pageMatch ? Number(pageMatch[2]) : undefined,
    total: totalMatch ? Number(totalMatch[1]) : undefined,
  };
}

export function captureScreenContext(): AssistantScreenContext {
  if (typeof document === "undefined") return {};

  const main = document.querySelector("main") ?? document.body;

  return {
    route: `${window.location.pathname}${window.location.search}`,
    title: readTitle(main),
    resource: readResource(window.location.pathname),
    filters: readFilters(window.location.search),
    pagination: readPagination(document),
    records: readTableRecords(main),
    selection: readDetail(main),
  };
}
