// K04 Chips: exact places evidence came from, and the file or folder in scope. Mono text; paths never truncate.
import { BookOpen, FileText, Folder, MessageSquare } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { source as sourceCopy } from "@/copy/en";
import { cn } from "@/lib/utils";

/** The contract's three source kinds (proposal.schema.yaml). */
import type { Source } from "@/contracts/proposal";
export type {
  FileSource,
  LineSource,
  PersonSource,
  PlaceSource,
  Source,
} from "@/contracts/proposal";

const chipClass =
  "inline-flex max-w-full items-center whitespace-nowrap gap-km-2 rounded-sm border-hairline border-border bg-secondary px-km-3 py-km-1 text-xs leading-xs text-foreground";

/**
 * A name that may wrap only at a space or after "/": never at a hyphen or mid-name.
 * Use it wherever a file name sits in text that can wrap.
 */
export function NoBreakName({ children }: { children: string }) {
  // Words keep their spaces between them; a word with "/" may break after each "/".
  return (
    <>
      {children.split(/(\s+)/).map((word, i) =>
        /^\s*$/.test(word) ? (
          word
        ) : (
          <span key={i}>
            {word.split(/(?<=\/)/).map((piece, k) => (
              <span key={k}>
                {k > 0 && <wbr />}
                <span className="inline-block max-w-full wrap-anywhere">
                  {piece}
                </span>
              </span>
            ))}
          </span>
        ),
      )}
    </>
  );
}

function Chip({
  icon: Icon,
  mono = true,
  className,
  title,
  children,
}: {
  icon: LucideIcon;
  mono?: boolean;
  className?: string;
  /** Shown on hover, such as the full path behind a file name. */
  title?: string;
  children: ReactNode;
}) {
  return (
    <span className={cn(chipClass, className)} title={title}>
      <Icon aria-hidden className="size-km-icon shrink-0" />
      <span
        className={cn(
          "min-w-0 whitespace-normal",
          mono && "font-(family-name:--font-mono)",
        )}
      >
        {typeof children === "string" ? (
          <NoBreakName>{children}</NoBreakName>
        ) : (
          children
        )}
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
  if (!("line_number" in source))
    return (
      <Chip icon={FileText} className={className}>
        {source.file}
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
  title,
}: {
  path: string;
  folder?: boolean;
  className?: string;
  title?: string;
}) {
  return (
    <Chip
      icon={folder ? Folder : FileText}
      mono={!folder}
      className={className}
      title={title}
    >
      {path}
    </Chip>
  );
}
