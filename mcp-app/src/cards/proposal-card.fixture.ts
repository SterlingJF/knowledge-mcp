// Realistic proposal data matching frame E02, shared by the test and the gallery.
import type { Proposal } from "@/contracts/proposal";

export const e02: Proposal = {
  schema: "knowledge-mcp/proposal/1",
  summary: "Focus the proposal on retiring the evening build",
  rows: [
    {
      current: { label: "Title", text: "Cache proposal" },
      proposed: { label: "Title", text: "Retire the evening build" },
      mark: "supported",
      sources: [{ file: "meeting-notes.md", line_number: 4 }],
    },
    {
      current: { label: "Motivation", text: "Builds are slow." },
      proposed: {
        label: "Motivation",
        text: "The evening build takes 41 minutes and blocks releases.",
      },
      mark: "partly",
      sources: [{ file: "build-timings.xlsx", place: "Evening!A2:D10" }],
    },
    {
      current: { label: "Status", text: "Draft" },
      proposed: {
        label: "Status",
        text: "slide 7 approved, notes disputed",
      },
      mark: "conflicting",
      sources: [
        { file: "meeting-notes.md", line_number: 11 },
        { file: "meeting-notes.md", line_number: 19 },
      ],
    },
    {
      proposed: {
        label: "Open question",
        text: "Who owns the cache after launch?",
      },
      mark: "suggested",
      sources: [{ said: "ask who owns the cache" }],
    },
  ],
  left_out: [
    {
      file: "vendor-quote.xlsx",
      reason: "Pricing only; no claim about the build.",
    },
    { file: "release-calendar.md", reason: "Dates predate the proposal." },
  ],
  card: "Proposed changes to cache-proposal.md (C1–C4).",
  based_on: {
    document_digest:
      "sha256:3f1a9c0e7b2d4a6f8e1c3b5d7f9a0c2e4b6d8f0a1c3e5b7d9f1a3c5e7b9d1f3a",
  },
  instance: {
    subject: "docs/proposals/cache-proposal.md",
    created_at: "2026-10-28T09:41:00.000Z",
    seq: 1,
  },
};

export const newDocument: Proposal = {
  ...e02,
  summary: "A design proposal for retiring the evening build",
  rows: e02.rows.slice(0, 2).map((r) => ({ ...r, current: undefined })),
  left_out: undefined,
  instance: {
    created_at: "2026-10-28T09:41:00.000Z",
    seq: 2,
    subject: "docs/proposals/evening-build.md",
  },
};
