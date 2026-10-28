// A realistic move plan matching frames M01 and M05, shared by the test and the gallery.
import type { DocumentMoves } from "@/contracts/document-moves";

const d = (c: string) => `sha256:${c.repeat(64)}` as const;

export const m01: DocumentMoves = {
  schema: "knowledge-mcp/document-moves/1",
  location: "notes",
  status: "permission_needed",
  allowed_by: null,
  search: ["build-review-notes", "retire-evening", "timings-notes"],
  based_on: {
    listing_digest: d("a"),
    record_digest: d("b"),
    documents: [{ path: "Inbox/retire-evening.md", digest: d("c") }],
    configuration: [],
  },
  writes: [],
  record: null,
  digest: null,
  links: [
    {
      source_path: "decisions-index.md",
      start: 120,
      end: 138,
      target_before: "Inbox/retire-evening.md",
      target_after: "Decisions/2026-10-28 retire evening build.md",
      replacement: "[[2026-10-28 retire evening build]]",
    },
    {
      source_path: "cache-proposal.md",
      start: 410,
      end: 427,
      target_before: "Inbox/timings-notes.md",
      target_after: "Proposals/timings-notes.md",
      replacement: "[[Proposals/timings-notes]]",
    },
    {
      source_path: "weekly-2026-43.md",
      start: 70,
      end: 92,
      target_before: "Inbox/build-review-notes.md",
      target_after: "Meetings/2026-10-27 build review.md",
      replacement: "[[2026-10-27 build review]]",
    },
    {
      source_path: "weekly-2026-43.md",
      start: 200,
      end: 222,
      target_before: "Inbox/retire-evening.md",
      target_after: "Decisions/2026-10-28 retire evening build.md",
      replacement: "[[2026-10-28 retire evening build]]",
    },
    {
      source_path: "roadmap.md",
      start: 12,
      end: 30,
      target_before: "Inbox/timings-notes.md",
      target_after: "Proposals/timings-notes.md",
      replacement: "[[Proposals/timings-notes]]",
    },
  ],
  issues: [],
  received: [],
  moves: [
    {
      old_path: "Inbox/build-review-notes.md",
      path: "Meetings/2026-10-27 build review.md",
    },
    {
      old_path: "Inbox/retire-evening.md",
      path: "Decisions/2026-10-28 retire evening build.md",
    },
    { old_path: "Inbox/timings-notes.md", path: "Proposals/timings-notes.md" },
  ],
  affected_documents: [],
  record_changes: [],
  summary: "File the new files",
  folder: "Inbox",
  stays: [{ path: "Inbox/scan-0412.md", reason: "no document type" }],
  naming: [
    { path: "Meetings/2026-10-27 build review.md", rule: "date + title" },
    {
      path: "Decisions/2026-10-28 retire evening build.md",
      rule: "date + title",
    },
  ],
};

export const m05: DocumentMoves = {
  ...m01,
  status: "blocked",
  issues: [
    {
      code: "name taken",
      source_path: "Decisions/2026-10-28 retire evening build.md",
      start: null,
      end: null,
      detail: "already exists",
      choices: [{ action: "skip_move", path: "Inbox/retire-evening.md" }],
    },
    {
      code: "ambiguous link",
      source_path: "weekly-2026-43.md",
      start: 40,
      end: 52,
      detail: "[[proposal]] matches 2 notes",
      choices: [
        { action: "bind_link", path: "Proposals/cache-proposal.md" },
        { action: "bind_link", path: "Proposals/timings-notes.md" },
      ],
    },
  ],
};

/** A blocker the server can compute no choice for. */
export const m05None: DocumentMoves = {
  ...m05,
  issues: [{ ...m05.issues[0], choices: undefined }],
};

/** M05 with only the blocker the card can answer: an ambiguous link. */
export const m05Link: DocumentMoves = { ...m05, issues: [m05.issues[1]] };
