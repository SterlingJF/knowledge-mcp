// Realistic proposal data matching frame E02, shared by the test and the gallery.
import type { Proposal } from "@/contracts/proposal";

export const e02: Proposal = {
  schema: "knowledge-mcp/proposal/1",
  summary: "Focus the proposal on retiring the evening build",
  rows: [
    {
      current: { label: "Title", text: "Build schedule and cache rollout" },
      proposed: { label: "Title", text: "Evening build retirement" },
      mark: "suggested",
      sources: [{ file: "meeting-notes.md", line_number: 15 }],
    },
    {
      current: { label: "Motivation", text: "evening build never finishes" },
      proposed: {
        label: "Motivation",
        text: "7 of 9 evening runs hit the 6-hour limit",
      },
      mark: "supported",
      sources: [{ file: "build-timings.xlsx", place: "Evening!A2:D10" }],
    },
    {
      proposed: { label: "Status", text: "slide 7 approved, notes disputed" },
      mark: "conflicting",
      sources: [
        { file: "cache-rollout-review.pptx", place: "slide 7" },
        { file: "meeting-notes.md", line_number: 11 },
        { file: "meeting-notes.md", line_number: 19 },
      ],
    },
    {
      current: {
        label: "Open question",
        text: "what baseline would show build times doubled?",
      },
      proposed: {
        label: "Still open",
        text: "no timings from before the cache",
      },
      mark: "partly",
      sources: [
        { file: "build-timings.xlsx", place: "Evening!A2" },
        { file: "meeting-notes.md", line_number: 21 },
      ],
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
  rows: e02.rows.map((r) => ({ ...r, current: undefined })),
  left_out: undefined,
  instance: {
    created_at: "2026-10-28T09:41:00.000Z",
    seq: 2,
    subject: "docs/proposals/evening-build.md",
  },
};
