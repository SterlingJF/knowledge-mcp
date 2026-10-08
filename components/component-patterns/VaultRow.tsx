// File: components/component-patterns/VaultRow.tsx

import { Button } from "../component-elements/button";
import { VaultRowMenu } from "../component-patterns/VaultRowMenu";
import { VaultRowRename } from "../component-patterns/VaultRowRename";
import { cn } from "../lib/utils";
import { TriangleAlert } from "lucide-react";

import type { VaultAction } from "../component-patterns/VaultRowMenu";
import type { Vault } from "../lib/types";

export type VaultRowProps = {
  vault: Vault;
  busy: boolean;
  canMove: boolean;
  isRenaming?: boolean;
  onOpen?: (path: string) => void;
  onAction: (action: VaultAction, vault: Vault) => void;
  onRenameSubmit?: (name: string) => Promise<boolean>;
  onRenameCancel?: () => void;
};

/** Open control and menu trigger are siblings. Nested interactive controls fail axe. */
export function VaultRow({
  vault,
  busy,
  canMove,
  isRenaming = false,
  onOpen,
  onAction,
  onRenameSubmit,
  onRenameCancel,
}: VaultRowProps) {
  const detail = (
    <>
      <span className="text-muted-foreground w-full font-mono text-xs break-all whitespace-normal">
        {vault.path}
      </span>
      {!vault.available ? (
        <span className="text-muted-foreground flex items-center gap-1 text-xs">
          <TriangleAlert aria-hidden="true" className="size-3" />
          This folder has moved or been deleted
        </span>
      ) : null}
    </>
  );

  return (
    <li
      className={cn(
        "group/vault-row flex items-start gap-[var(--space-xxs)] rounded-[var(--control-radius-md)] px-[var(--space-xxs)]",
        "hover:bg-[var(--sidebar-accent)] hover:text-[var(--sidebar-accent-foreground)]",
        !vault.available && "opacity-60",
      )}
    >
      {isRenaming && onRenameSubmit && onRenameCancel ? (
        // An input cannot sit inside a button.
        <div
          data-vault-renaming=""
          className="flex min-w-0 flex-1 flex-col items-start gap-0.5 px-[var(--space-xxs)] py-[var(--space-xs)]"
        >
          <VaultRowRename
            name={vault.name}
            busy={busy}
            onSubmit={onRenameSubmit}
            onCancel={onRenameCancel}
          />
          {detail}
        </div>
      ) : onOpen ? (
        <Button
          variant="ghost"
          data-vault-open=""
          // Row is two lines and the path wraps.
          className="h-auto min-w-0 flex-1 flex-col items-start gap-0.5 bg-transparent px-[var(--space-xxs)] py-[var(--space-xs)] text-left hover:bg-transparent"
          disabled={busy || !vault.available}
          onClick={() => onOpen(vault.path)}
        >
          <span className="truncate text-sm font-medium">{vault.name}</span>
          {detail}
        </Button>
      ) : (
        <div className="flex h-auto min-w-0 flex-1 flex-col items-start gap-0.5 px-[var(--space-xxs)] py-[var(--space-xs)] text-left">
          <span className="truncate text-sm font-medium">{vault.name}</span>
          {detail}
        </div>
      )}

      {/* Aligned to the name line. Row height varies with path wrap. */}
      <span className="mt-[var(--space-xxs)]">
        <VaultRowMenu
          vault={vault}
          disabled={busy}
          canMove={canMove}
          onAction={onAction}
        />
      </span>
    </li>
  );
}
