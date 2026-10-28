// K04 Chips: exact places evidence came from, and the file or folder in scope. Mono text; paths never truncate.
import { BookOpen, FileText, Folder, MessageSquare } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { source as sourceCopy } from "@/copy/en";
import { cn } from "@/lib/utils";

/** The contract's three source kinds (proposal.schema.yaml). */
export type LineSource = { file: string; line_number: number };
export type PlaceSource = { file: string; place: string };
export type PersonSource = { said: string };
export type Source = LineSource | PlaceSource | PersonSource;

const chipClass =
  "inline-flex items-center whitespace-nowrap gap-(--km-space-2) rounded-(--border-radius-sm) border-(length:--border-width-regular) border-(--color-border-tertiary) bg-(--color-background-primary) px-(--km-space-3) py-(--km-space-1) text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) text-(--color-text-primary)";

function Chip({
  icon: Icon,
  mono = true,
  className,
  children,
}: {
  icon: LucideIcon;
  mono?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span className={cn(chipClass, className)}>
      <Icon aria-hidden className="size-(--km-icon) shrink-0" />
      <span className={mono ? "font-(family-name:--font-mono)" : undefined}>
        {children}
      </span>
    </span>
  );
}

/** A slide in a deck reads as a page; every other place (a sheet range) as a file. */
function placeIcon(place: string): LucideIcon {
  return /^slide\b/i.test(place) ? BookOpen : FileText;
}

/**
 * One chip per source. `continuation` shows a line source as `:19` when the chip before it named the same file.
 */
export function SourceChip({
  source,
  continuation = false,
  className,
}: {
  source: Source;
  continuation?: boolean;
  className?: string;
}) {
  if ("said" in source)
    return (
      <Chip icon={MessageSquare} mono={false} className={className}>
        {sourceCopy.said(source.said)}
      </Chip>
    );
  if ("place" in source)
    return (
      <Chip icon={placeIcon(source.place)} className={className}>
        {sourceCopy.place(source.file, source.place)}
      </Chip>
    );
  return (
    <Chip icon={FileText} className={className}>
      {continuation
        ? sourceCopy.sameFile(source.line_number)
        : sourceCopy.line(source.file, source.line_number)}
    </Chip>
  );
}

/** A file or folder in scope. */
export function PathChip({
  path,
  folder = false,
  className,
}: {
  path: string;
  folder?: boolean;
  className?: string;
}) {
  return (
    <Chip
      icon={folder ? Folder : FileText}
      mono={!folder}
      className={className}
    >
      {path}
    </Chip>
  );
}
