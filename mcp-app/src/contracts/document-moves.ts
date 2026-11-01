// The structuredContent of a kb_prepare_document_moves answer, mirroring
// contracts/extensions/mcp/v1/document-moves.schema.yaml (knowledge-mcp/document-moves/1).
// Edit the schema first; keep these types in step with it.
import type { Digest } from "./proposal";

export type MoveStatus =
  "texts_needed" | "permission_needed" | "ready" | "blocked" | "unchanged";

export type AllowedBy = {
  basis: "request" | "instruction" | "accepted_change";
  text: string;
  location?: string;
};

export type DocumentMove = { old_path: string; path: string };

export type Received = { name: string; digest: Digest };

export type MoveWrite = {
  old_path: string;
  path: string;
  before_digest: Digest;
  after_digest: Digest;
  text: string;
};

export type MoveLink = {
  source_path: string;
  /** Code-point offsets of the link token in the supplied text. */
  start: number;
  end: number;
  target_before: string;
  target_after: string;
  /** The replacement token, or null when the link needs no change. */
  replacement: string | null;
};

export type MoveChoice = {
  /** skip_move drops the move of path; bind_link binds the issue's link to path. */
  action: "skip_move" | "bind_link";
  path: string;
};

export type MoveStay = { path: string; reason: string };
export type MoveNaming = { path: string; rule: string };

export type MoveIssue = {
  code: string;
  source_path: string | null;
  start: number | null;
  end: number | null;
  detail: string;
  /** Resolutions the server can compute; absent when none. */
  choices?: Array<MoveChoice>;
};

export type DocumentMoves = {
  schema: "knowledge-mcp/document-moves/1";
  location: string;
  status: MoveStatus;
  allowed_by: AllowedBy | null;
  search: Array<string>;
  based_on: {
    listing_digest: Digest;
    record_digest: Digest;
    documents: Array<{ path: string; digest: Digest }>;
    configuration: Array<Received>;
  };
  writes: Array<MoveWrite>;
  record: string | null;
  digest: Digest | null;
  links: Array<MoveLink>;
  issues: Array<MoveIssue>;
  received: Array<Received>;
  moves: Array<DocumentMove>;
  affected_documents: Array<DocumentMove>;
  record_changes: Array<DocumentMove>;
  /** Echoed from the assistant's input. */
  summary?: string;
  folder?: string;
  stays?: Array<MoveStay>;
  naming?: Array<MoveNaming>;
  /** The move plan as Markdown, for hosts without the app. */
  card?: string;
};
