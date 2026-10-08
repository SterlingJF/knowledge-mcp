// File: components/component-patterns/VaultList.tsx

import { VaultRow } from "../component-patterns/VaultRow";
import { useState } from "react";

import type { VaultAction } from "../component-patterns/VaultRowMenu";
import type { Vault } from "../lib/types";

export type VaultListProps = {
  vaults: Array<Vault>;
  busy: boolean;
  canMove: boolean;
  onOpen?: (path: string) => void;
  onAction: (action: VaultAction, vault: Vault) => void;
  /** True after backend accepts rename. */
  onRename: (vault: Vault, name: string) => Promise<boolean>;
};

/** Fragment in pane's flex column. Handles rename state and intercepts rename actions. */
export function VaultList({
  vaults,
  busy,
  canMove,
  onOpen,
  onAction,
  onRename,
}: VaultListProps) {
  const [renamingId, setRenamingId] = useState<string | null>(null);

  return (
    <>
      <h2 className="text-muted-foreground pb-[var(--space-xs)] pl-[var(--space-xxs)] text-xs font-medium tracking-wide uppercase">
        Your vaults
      </h2>
      {vaults.length === 0 ? (
        <p className="text-muted-foreground px-[var(--space-xxs)] text-sm">
          No vaults yet. Create one, or open a folder you already have.
        </p>
      ) : (
        <ul className="flex flex-col gap-[var(--space-xxs)]">
          {vaults.map((vault) => (
            <VaultRow
              key={vault.id}
              vault={vault}
              busy={busy}
              canMove={canMove}
              isRenaming={vault.id === renamingId}
              onOpen={onOpen}
              onAction={(action, target) => {
                if (action !== "rename") {
                  onAction(action, target);
                  return;
                }
                setRenamingId(target.id);
              }}
              onRenameSubmit={async (name) => {
                const took = await onRename(vault, name);
                if (took) setRenamingId(null);
                return took;
              }}
              onRenameCancel={() => setRenamingId(null)}
            />
          ))}
        </ul>
      )}
    </>
  );
}
