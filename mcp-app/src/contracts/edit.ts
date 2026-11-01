// The structuredContent of a kb_record_edit result, mirroring
// contracts/extensions/mcp/v1/edit.schema.yaml (knowledge-mcp/edit/2).
// Edit the schema first; keep these types in step with it.
import type { Digest } from "./proposal";

export type AllowedBy = {
  basis: "request" | "instruction" | "accepted_change";
  /** The request, instruction or accepted change, quoted. */
  text: string;
};

export type EditOperation = {
  id: string;
  /** One-based position within the operation. */
  index: number;
  count: number;
  old_path: string;
  path: string;
};

export type Edit = {
  schema: "knowledge-mcp/edit/2";
  /** 32 lowercase hex digits. */
  id: string;
  /** ISO-8601 UTC. */
  time: string;
  location: string;
  allowed_by: AllowedBy;
  /** Present when the edit replaced the whole file. */
  whole_file?: true;
  before_digest: Digest;
  after_digest: Digest;
  /** Present for one edit of a multi-file operation; whole_file is then true. */
  operation?: EditOperation;
  /** Set when the whole-file edit started from empty text. */
  created?: true;
  /** The edit this one undoes. */
  undoes?: { id: string; time: string };
  changes?: EditChanges;
  /** The saved edit as markdown, for hosts without the app. */
  card: string;
};

export type ChangedLine = { change: "removed" | "added"; text: string };

export type EditChanges = {
  hunks: number;
  /** In document order, at most 12. */
  lines: Array<ChangedLine>;
  /** Changed lines beyond `lines`. */
  more: number;
};
