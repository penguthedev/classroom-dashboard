import { Fragment, type ReactNode } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const INLINE_PATTERN =
  /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(INLINE_PATTERN).filter((part) => part !== "");

  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;

    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={key} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("__") && part.endsWith("__")) {
      return (
        <strong key={key} className="font-semibold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={key}
          className="rounded bg-muted px-1 py-0.5 font-mono text-[0.8em]"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }

    const link = part.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/);
    if (link) {
      return (
        <a
          key={key}
          href={link[2]}
          target="_blank"
          rel="noreferrer"
          className="text-primary underline underline-offset-2"
        >
          {link[1]}
        </a>
      );
    }

    return <Fragment key={key}>{part}</Fragment>;
  });
}

function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isDivider(line: string): boolean {
  return /^\|?[\s:-]+\|[\s:|-]*$/.test(line.trim()) && line.includes("-");
}

export function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];

  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let code: string[] | null = null;
  let index = 0;

  function flushParagraph() {
    if (paragraph.length === 0) return;
    blocks.push(
      <p key={`p-${blocks.length}`} className="leading-relaxed">
        {renderInline(paragraph.join(" "), `p-${blocks.length}`)}
      </p>,
    );
    paragraph = [];
  }

  function flushList() {
    if (!list) return;
    const { ordered, items } = list;
    const ListTag = ordered ? "ol" : "ul";
    blocks.push(
      <ListTag
        key={`l-${blocks.length}`}
        className={
          ordered
            ? "list-decimal space-y-1 pl-5 leading-relaxed"
            : "list-disc space-y-1 pl-5 leading-relaxed"
        }
      >
        {items.map((item, itemIndex) => (
          <li key={itemIndex}>{renderInline(item, `li-${blocks.length}-${itemIndex}`)}</li>
        ))}
      </ListTag>,
    );
    list = null;
  }

  function flushAll() {
    flushParagraph();
    flushList();
  }

  while (index < lines.length) {
    const line = lines[index];

    if (line.trim().startsWith("```")) {
      if (code) {
        blocks.push(
          <pre
            key={`c-${blocks.length}`}
            className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs"
          >
            {code.join("\n")}
          </pre>,
        );
        code = null;
      } else {
        flushAll();
        code = [];
      }
      index += 1;
      continue;
    }

    if (code) {
      code.push(line);
      index += 1;
      continue;
    }

    if (!line.trim()) {
      flushAll();
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      flushAll();
      const level = heading[1].length;
      blocks.push(
        <p
          key={`h-${blocks.length}`}
          className={
            level <= 2
              ? "mt-1 text-sm font-semibold text-foreground"
              : "mt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground"
          }
        >
          {renderInline(heading[2], `h-${blocks.length}`)}
        </p>,
      );
      index += 1;
      continue;
    }

    if (
      line.includes("|") &&
      index + 1 < lines.length &&
      isDivider(lines[index + 1])
    ) {
      flushAll();
      const headers = splitRow(line);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        rows.push(splitRow(lines[index]));
        index += 1;
      }
      blocks.push(
        <div key={`t-${blocks.length}`} className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                {headers.map((header, headerIndex) => (
                  <TableHead key={headerIndex}>{header}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row, rowIndex) => (
                <TableRow key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <TableCell key={cellIndex}>
                      {renderInline(cell, `td-${rowIndex}-${cellIndex}`)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>,
      );
      continue;
    }

    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    if (bullet) {
      flushParagraph();
      if (!list || list.ordered) {
        flushList();
        list = { ordered: false, items: [] };
      }
      list.items.push(bullet[1]);
      index += 1;
      continue;
    }

    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (numbered) {
      flushParagraph();
      if (!list || !list.ordered) {
        flushList();
        list = { ordered: true, items: [] };
      }
      list.items.push(numbered[1]);
      index += 1;
      continue;
    }

    flushList();
    paragraph.push(line.trim());
    index += 1;
  }

  flushAll();
  if (code && code.length > 0) {
    blocks.push(
      <pre
        key={`c-${blocks.length}`}
        className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs"
      >
        {code.join("\n")}
      </pre>,
    );
  }

  return <div className="space-y-2 text-sm">{blocks}</div>;
}
