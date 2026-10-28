// The last path segment of a location, for card titles and messages.

/** `Proposals/cache-proposal.md` → `cache-proposal.md`; empty when the path ends in `/`. */
export const lastSegment = (path: string) => path.split("/").at(-1) ?? "";
