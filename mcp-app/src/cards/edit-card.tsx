// C-Result: the card for a kb_record_edit result (knowledge-mcp/edit/2).
// It says what was saved or created, when and on whose OK, with Undo. Undo only sends a message:
// the assistant checks the edit log and restores the file, and the undo comes back as its own card.
import type { ToolResult } from "@/bridge/bridge";
import { useCardLifecycle } from "@/component-patterns/card-lifecycle";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { ResultCard } from "@/component-patterns/result-card";
import type { Edit } from "@/contracts/edit";
import { badge, editResult, meta } from "@/copy/en";
import { registerCard } from "./registry";
import type { CardProps } from "./registry";

/** The digest of empty text: an edit from it created the file. */
export const EMPTY_DIGEST =
  "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

const DIGEST = /^sha256:[0-9a-f]{64}$/;
const BASES = ["request", "instruction", "accepted_change"];

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
    DIGEST.test(e.after_digest)
  );
}

export const isCreated = (e: Edit) => e.before_digest === EMPTY_DIGEST;

export const fileName = (e: Edit) => e.location.split("/").at(-1) || e.location;

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
};

/** The drawn card, given its state; the gallery renders it with fixed lifecycles. */
export function EditView({ edit, lifecycle, timeZone }: EditViewProps) {
  const created = isCreated(edit);
  const message = undoMessage(edit, timeZone);
  // ResultCard owns the Undo action; the context rides along on the press.
  const tracked: CardLifecycle = {
    ...lifecycle,
    press: (a) =>
      lifecycle.press(
        a.message === message ? { ...a, context: undoContext(edit) } : a,
      ),
  };
  return (
    <ResultCard
      kind="result"
      eyebrow={created ? editResult.created : editResult.saved}
      title={edit.location}
      badgeLabel={created ? badge.done.created : badge.done.saved}
      when={when(edit.time, timeZone).full}
      who={
        edit.allowed_by.basis === "instruction"
          ? editResult.allowedByInstruction
          : meta.approvedByYou
      }
      undoMessage={message}
      lifecycle={tracked}
    />
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
