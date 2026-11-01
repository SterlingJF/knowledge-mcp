// Real-shaped kb_record_edit results for the C-Result tests and gallery.
import type { Edit } from "@/contracts/edit";

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
  changes: {
    hunks: 4,
    lines: [
      { change: "removed", text: "Title: Build schedule and cache rollout" },
      { change: "added", text: "Title: Evening build retirement" },
      { change: "removed", text: "Motivation: evening build never finishes" },
      {
        change: "added",
        text: "Motivation: 7 of 9 evening runs hit the 6-hour limit",
      },
      { change: "added", text: "Status: Proposed. Approval is disputed." },
      { change: "added", text: "Still open: no timings from before the cache" },
    ],
    more: 0,
  },
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
  created: true,
  changes: undefined,
  before_digest:
    "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  card: "**Created** Proposals/cache-rollout.md",
};

/** R03: the undo of r01, recorded three minutes later. */
export const r03: Edit = {
  ...r01,
  id: "9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b",
  time: "2026-10-28T09:44:02.118Z",
  allowed_by: {
    basis: "request",
    text: "Undo the 09:41 edit to cache-proposal.md",
  },
  undoes: { id: r01.id, time: r01.time },
  before_digest: r01.after_digest,
  after_digest: r01.before_digest,
  changes: {
    hunks: 4,
    lines: (r01.changes?.lines ?? []).map((l) => ({
      change: l.change === "added" ? ("removed" as const) : ("added" as const),
      text: l.text,
    })),
    more: 0,
  },
};

/** A long edit: twelve lines shown, five more counted. */
export const long: Edit = {
  ...r01,
  changes: {
    hunks: 7,
    lines: Array.from({ length: 12 }, (_, i) => ({
      change: "added" as const,
      text: `Line ${i + 1}`,
    })),
    more: 5,
  },
};
