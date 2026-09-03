# How writes are refused

What happens when an agent writes somewhere it shouldn't. The store resolves and refuses; it
never picks a location, never renames, never overwrites silently.

## The refusals

- **A path outside the declared folders.** Creating `Scratch/note.md` is refused with the folders
  that would have been accepted. The store does not relocate it to a near-fit.
- **A path escaping the vault.** `../` and absolute paths are refused outright.
- **A collision.** Creating a file where one exists is a 409. There is no `-2` suffix, no silent
  rename — the caller renames or reconsiders.
- **A stale update.** Every single-artifact read carries an ETag computed from the file's bytes at
  read time — it is never stored, so a person hand-editing the file moves it. PUT requires that
  value in `If-Match`: omission is 428 and a stale value is 409.
- **A write in someone else's name.** An agent may only assert records as itself. Sending a
  person's record, even unchanged, is refused.
- **A commit.** Committing is a person's act. `km_commit_artifact` is designed to be refused —
  the agent's job is to relay that the draft is ready and present the returned `personRequest`.

## Why refusal instead of correction

If the store fixed a bad write itself — renamed a colliding file, relocated a misplaced one —
the agent would keep working from a wrong picture of the vault, and the mistake would surface
later, somewhere else. A refusal surfaces it immediately, with the reason, while the agent can
still fix it in the same exchange.

## What a refusal looks like

Refusals arrive as typed errors with the reason in plain words, and successful MCP requests carry
a `_request` receipt (method, URL, status, elapsed, and response ETag when present) so the exchange
can be audited afterward.
