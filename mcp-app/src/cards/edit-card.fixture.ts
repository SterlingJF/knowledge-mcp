// Real-shaped kb_record_edit results for the C-Result tests and gallery.
import type { Edit } from "@/contracts/edit";
import { EMPTY_DIGEST } from "./edit-card";

/** R01: the four approved changes saved to cache-proposal.md. */
export const r01: Edit = {
  schema: "knowledge-mcp/edit/2",
  id: "4f1c9a2e7b3d4c5e8f9a0b1c2d3e4f5a",
  time: "2026-10-28T09:41:07.312Z",
  location: "Proposals/cache-proposal.md",
  allowed_by: {
    basis: "accepted_change",
    text: "Save C1–C4 to cache-proposal.md",
  },
  before_digest:
    "sha256:9b2f1e0c3d4a5b6c7d8e9f00112233445566778899aabbccddeeff0011223344",
  after_digest:
    "sha256:1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e7f809",
  card: "**Saved** Proposals/cache-proposal.md · recorded 2026-10-28 09:41 UTC",
};

/** D06: Proposals/cache-rollout.md created from nothing. */
export const d06: Edit = {
  ...r01,
  id: "0a1b2c3d4e5f60718293a4b5c6d7e8f9",
  time: "2026-10-28T10:12:44.020Z",
  location: "Proposals/cache-rollout.md",
  allowed_by: {
    basis: "request",
    text: "Create Proposals/cache-rollout.md with C1–C3",
  },
  whole_file: true,
  before_digest: EMPTY_DIGEST,
  card: "**Created** Proposals/cache-rollout.md",
};
