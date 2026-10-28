// The structuredContent of a kb_prepare_proposal result, mirroring
// contracts/extensions/mcp/v1/proposal.schema.yaml (knowledge-mcp/proposal/1).
// Edit the schema first; keep these types in step with it.

export type ProposalCell = { label?: string; text: string };

export type EvidenceMark = "supported" | "partly" | "conflicting" | "suggested";

export type LineSource = { file: string; line_number: number };
export type PlaceSource = { file: string; place: string };
export type PersonSource = { said: string };
export type Source = LineSource | PlaceSource | PersonSource;

export type ProposalRow = {
  /** The document's text now; absent for an addition. */
  current?: ProposalCell;
  proposed: ProposalCell;
  mark?: EvidenceMark;
  sources: Array<Source>;
};

export type LeftOutFile = { file: string; reason: string };

export type Proposal = {
  schema: "knowledge-mcp/proposal/1";
  summary: string;
  /** Row n is change Cn. */
  rows: Array<ProposalRow>;
  left_out?: Array<LeftOutFile>;
  /** The Markdown text card, for hosts without the app. */
  card: string;
};
