// The structuredContent of a kb_prepare_proposal result, mirroring
// contracts/extensions/mcp/v1/proposal.schema.yaml (knowledge-mcp/proposal/1).
// Edit the schema first; keep these types in step with it.

export type ProposalCell = { label?: string; text: string };

export type EvidenceMark = "supported" | "partly" | "conflicting" | "suggested";

export type LineSource = { file: string; line_number: number };
export type PlaceSource = { file: string; place: string };
export type PersonSource = { said: string };
/** A whole file, with no line or place, such as a sheet read in full. */
export type FileSource = { file: string };
export type Source = LineSource | PlaceSource | FileSource | PersonSource;

export type ProposalRow = {
  /** The document's text now; absent for an addition. */
  current?: ProposalCell;
  proposed: ProposalCell;
  mark?: EvidenceMark;
  sources: Array<Source>;
};

export type Filing =
  | { path: string; naming_rule: string; reason?: string }
  | { path: string; naming_rule: null; reason: string };

export type LeftOutFile = { file: string; reason: string };

export type Proposal = {
  schema: "knowledge-mcp/proposal/1";
  summary: string;
  /** Row n is change Cn. */
  rows: Array<ProposalRow>;
  /** The document's type, from kb_get_document_type. */
  document_type?: { id: string; label: string };
  /** Who the document is for; `confirmed` is false when the assistant guessed. */
  reader?: { id: string; label: string; confirmed: boolean };
  /** For a new document: where it will be saved and whether a naming rule applied. */
  filing?: Filing;
  /** Questions no source answers, apart from conflicting rows. */
  open_questions?: Array<ProposalCell>;
  left_out?: Array<LeftOutFile>;
  /** The Markdown text card, for hosts without the app. */
  card: string;
  /** The document text the proposal was prepared against; present when the assistant sent its digest. */
  based_on?: { document_digest: Digest };
  /** Server-minted key: a card stands down when a younger one about the same subject appears. */
  instance?: ProposalInstance;
};

/** `sha256:` plus 64 lowercase hex digits (common.schema.yaml digest). */
export type Digest = `sha256:${string}`;

export type ProposalInstance = {
  /** The document's location as the assistant sent it. */
  subject: string;
  /** Server wall-clock time, ISO-8601 UTC to the millisecond. */
  created_at: string;
  /** Per-process counter; breaks ties in created_at. */
  seq: number;
};
