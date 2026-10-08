// File: components/component-patterns/VaultRowMenu.tsx

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../component-core/dropdown-menu";
import { Button } from "../component-elements/button";
import {
  Copy,
  FolderInput,
  FolderOpen,
  MoreHorizontal,
  Pencil,
  X,
} from "lucide-react";

import type { Vault } from "../lib/types";

export type VaultAction = "copy-id" | "rename" | "move" | "reveal" | "remove";

export type VaultRowMenuProps = {
  vault: Vault;
  disabled: boolean;
  /** Folder-picker availability. Move requires it. */
  canMove: boolean;
  onAction: (action: VaultAction, vault: Vault) => void;
};

/** Uses `Button`. `IconActionButton` opts into page-wide tooltip sweep. */
export function VaultRowMenu({
  vault,
  disabled,
  canMove,
  onAction,
}: VaultRowMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            disabled={disabled}
            aria-label={`More actions for ${vault.name}`}
            // app-menu-row-action sets size and background. No bg-* or size-* here.
            // Base UI returns focus to trigger on close.
            className="app-menu-row-action shrink-0 opacity-0 transition-opacity duration-[var(--duration-fast)] ease-[var(--ease-fade)] group-hover/vault-row:opacity-100 group-has-[:focus-visible]/vault-row:opacity-100 motion-reduce:duration-[var(--duration-reduced)] aria-expanded:opacity-100"
          >
            <MoreHorizontal aria-hidden="true" />
          </Button>
        }
      />
      <DropdownMenuContent side="right" align="start" className="w-56">
        <DropdownMenuItem onClick={() => onAction("copy-id", vault)}>
          <Copy aria-hidden="true" />
          Copy vault ID
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onAction("rename", vault)}>
          <Pencil aria-hidden="true" />
          Rename vault…
        </DropdownMenuItem>
        <DropdownMenuItem
          disabled={!canMove}
          onClick={() => onAction("move", vault)}
        >
          <FolderInput aria-hidden="true" />
          Move vault…
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onAction("reveal", vault)}>
          <FolderOpen aria-hidden="true" />
          Reveal vault in Finder
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          onClick={() => onAction("remove", vault)}
        >
          <X aria-hidden="true" />
          Remove from list
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
