// C-Result: the card for a kb_record_edit result (knowledge-mcp/edit/2).
// It says what was saved, created or undone, when and on whose OK, with Undo. Undo only sends a message:
// the assistant checks the edit log and restores the file, and the undo comes back as its own card.
import { useId, useState } from "react";

import type { ToolResult } from "@/bridge/bridge";
import { Diff } from "@/component-elements/diff";
import { useCardLifecycle } from "@/component-patterns/card-lifecycle";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { ResultCard } from "@/component-patterns/result-card";
import type { Edit, EditChanges } from "@/contracts/edit";
import { action, badge, change, editResult, eyebrow, meta } from "@/copy/en";
import { lastSegment } from "./file-name";
import { registerCard } from "./registry";
import type { CardProps } from "./registry";

const DIGEST = /^sha256:[0-9a-f]{64}$/;
const BASES = ["request", "instruction", "accepted_change"];

function isChanges(c: unknown): c is EditChanges {
  if (typeof c !== "object" || c === null) return false;
  const { hunks, lines, more } = c as Partial<EditChanges>;
  return (
    typeof hunks === "number" &&
    typeof more === "number" &&
    Array.isArray(lines) &&
    lines.every(
      (l) =>
        typeof l === "object" &&
        l !== null &&
        (l.change === "removed" || l.change === "added") &&
        typeof l.text === "string",
    )
  );
}

export function isEdit(result: ToolResult | null): result is ToolResult & Edit {
  if (!result || result.schema !== "knowledge-mcp/edit/2") return false;
  const e = result as Partial<Edit>;
  return (
    typeof e.id === "string" &&
    typeof e.time === "string" &&
    !Number.isNaN(Date.parse(e.time)) &&
    typeof e.location === "string" &&
    e.location.length > 0 &&
    typeof e.allowed_by === "object" &&
    e.allowed_by !== null &&
    BASES.includes(e.allowed_by.basis) &&
    typeof e.before_digest === "string" &&
    DIGEST.test(e.before_digest) &&
    typeof e.after_digest === "string" &&
    DIGEST.test(e.after_digest) &&
    (e.changes === undefined || isChanges(e.changes)) &&
    (e.undoes === undefined ||
      (typeof e.undoes === "object" &&
        e.undoes !== null &&
        typeof e.undoes.id === "string" &&
        typeof e.undoes.time === "string" &&
        !Number.isNaN(Date.parse(e.undoes.time))))
  );
}

export const fileName = (e: Edit) => lastSegment(e.location) || e.location;

/** `Oct 28, 09:41` and `09:41`, in the viewer's time zone unless one is given. */
export function when(iso: string, timeZone?: string) {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone,
  });
  const day = d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone,
  });
  return { full: `${day}, ${time}`, time };
}

/** D06: a created file's full location. Otherwise `cache-proposal.md · 4 changes`, or the file name alone. */
export const editTitle = (e: Edit) =>
  e.created
    ? e.location
    : e.changes
      ? fileName(e) + meta.join + change.count(e.changes.hunks)
      : fileName(e);

export const undoMessage = (e: Edit, timeZone?: string) =>
  editResult.undo(when(e.time, timeZone).time, fileName(e));

export function undoContext(e: Edit) {
  return {
    edit: {
      id: e.id,
      location: e.location,
      time: e.time,
      before_digest: e.before_digest,
      after_digest: e.after_digest,
      ...(e.operation ? { operation: e.operation } : {}),
    },
  };
}

export type EditViewProps = {
  edit: Edit;
  lifecycle: CardLifecycle;
  timeZone?: string;
  /** The diff's open state; the gallery fixes it, the live card holds it. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

/** The drawn card, given its state; the gallery renders it with fixed lifecycles. */
export function EditView({
  edit,
  lifecycle,
  timeZone,
  open: fixedOpen,
  onOpenChange,
}: EditViewProps) {
  const [ownOpen, setOwnOpen] = useState(false);
  const diffId = useId();
  const open = fixedOpen ?? ownOpen;
  const setOpen = onOpenChange ?? setOwnOpen;
  const message = undoMessage(edit, timeZone);
  // R03 draws an undone card bare: no Undo, no change to open.
  const changes =
    !edit.undoes && edit.changes && edit.changes.lines.length > 0
      ? edit.changes
      : undefined;
  // ResultCard owns the Undo action; the context rides along on the press.
  const tracked: CardLifecycle = {
    ...lifecycle,
    press: (a) =>
      lifecycle.press(
        a.message === message ? { ...a, context: undoContext(edit) } : a,
      ),
  };
  const who = edit.undoes
    ? editResult.undoes(when(edit.undoes.time, timeZone).time)
    : edit.allowed_by.basis === "instruction"
      ? editResult.allowedByInstruction
      : meta.approvedByYou;
  return (
    <ResultCard
      kind="result"
      eyebrow={edit.created ? editResult.document : eyebrow.change}
      title={editTitle(edit)}
      badgeLabel={
        edit.created
          ? badge.done.created
          : edit.undoes
            ? badge.done.undone
            : badge.done.saved
      }
      when={when(edit.time, timeZone).full}
      who={who}
      // An undone change is redone through chat (R03).
      undoMessage={edit.undoes ? undefined : message}
      disclosure={
        changes
          ? {
              label: open ? action.hideChange : action.showChange,
              expanded: open,
              onToggle: () => setOpen(!open),
              controls: diffId,
            }
          : undefined
      }
      frozenBadge={badge.neutral.undoRequested}
      lifecycle={tracked}
    >
      {changes && open && (
        <div id={diffId}>
          <Diff
            lines={changes.lines.map((l) => ({ kind: l.change, text: l.text }))}
          />
          {changes.more > 0 && (
            <p className="mt-[var(--km-space-3)] text-[length:var(--font-text-xs-size)] text-[color:var(--color-text-secondary)]">
              {editResult.moreLines(changes.more)}
            </p>
          )}
        </div>
      )}
    </ResultCard>
  );
}

function LiveEdit({ edit }: { edit: Edit }) {
  const lifecycle = useCardLifecycle();
  return <EditView edit={edit} lifecycle={lifecycle} />;
}

export function EditCard({ result }: CardProps) {
  if (!isEdit(result)) return null;
  return <LiveEdit key={result.id} edit={result} />;
}

registerCard("knowledge-mcp/edit/2", EditCard);
