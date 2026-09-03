// File: launcher/src/component-patterns/VaultSwitcher.tsx

import { AppShell } from '@/component-patterns/AppShell'
import { VaultActions } from '@/component-patterns/VaultActions'
import { VaultCreate } from '@/component-patterns/VaultCreate'
import { VaultList } from '@/component-patterns/VaultList'
import { cn } from '@/lib/utils'
import { useEffect, useRef, useState } from 'react'

import type { VaultAction } from '@/component-patterns/VaultRowMenu'
import type { Vault } from '@/lib/backend'

export type VaultSwitcherView = 'actions' | 'create'

export type VaultSwitcherProps = {
  vaults: Array<Vault>
  version: string
  busy: boolean
  /** Last operation error text. */
  refusal: string | null
  defaultView?: VaultSwitcherView
  onOpenVault?: (path: string) => void
  onOpenFolder?: () => void
  onPickFolder?: () => Promise<string | null>
  onCreateVault: (parent: string, name: string) => Promise<boolean>
  onVaultAction: (action: VaultAction, vault: Vault) => void
  onRenameVault: (vault: Vault, name: string) => Promise<boolean>
  autostart?: boolean
  onAutostartChange?: (enabled: boolean) => void
}

/** `document` shape is measure-capped (ui-shell-patterns.css). */
export function VaultSwitcher({
  vaults,
  version,
  busy,
  refusal,
  defaultView = 'actions',
  onOpenVault,
  onOpenFolder,
  onPickFolder,
  onCreateVault,
  onVaultAction,
  onRenameVault,
  autostart,
  onAutostartChange,
}: VaultSwitcherProps) {
  const [view, setView] = useState<VaultSwitcherView>(defaultView)
  const actionsPaneRef = useRef<HTMLDivElement>(null)
  const createPaneRef = useRef<HTMLDivElement>(null)
  const movedRef = useRef(false)

  // Focus is ignored in an inert subtree. movedRef limits focus to view changes.
  useEffect(() => {
    if (!movedRef.current) return
    movedRef.current = false
    const target =
      view === 'create'
        ? createPaneRef.current?.querySelector<HTMLElement>('input')
        : actionsPaneRef.current?.querySelector<HTMLElement>(
            '[data-vault-create]',
          )
    target?.focus()
  }, [view])

  const show = (next: VaultSwitcherView) => {
    movedRef.current = true
    setView(next)
  }

  return (
    <AppShell
      primaryContributions={[]}
      navigationCommands={[]}
      viewCommands={[]}
      mainContextCommands={[]}
      trailingCommands={[]}
      mainContentShape="collection"
      leftSidebarChrome="none"
      // Overlaid title bar leaves no native drag region.
      windowGrip={<div data-tauri-drag-region className="size-full" />}
      leftSidebarHeader={null}
      leftSidebarLabel="Vaults"
      leftSidebar={
        <VaultList
          vaults={vaults}
          busy={busy}
          canMove={onPickFolder !== undefined}
          onOpen={onOpenVault}
          onAction={onVaultAction}
          onRename={onRenameVault}
        />
      }
    >
      <div className="flex h-full min-h-0 flex-col items-center justify-center px-[var(--space-xl)] py-[var(--space-lg)]">
        <div className="w-full max-w-lg space-y-[var(--space-xl)]">
          <div className="flex flex-col items-center gap-[var(--space-sm)]">
            <p className="text-xl font-semibold tracking-tight">
              Knowledge MCP
            </p>
            <p className="text-muted-foreground text-xs">Version {version}</p>
          </div>

          {/* Track holds the taller pane's height. Panes stay top-aligned. */}
          <div className="overflow-hidden" data-vault-track={view}>
            <div
              className={cn(
                'flex items-start transition-transform duration-[var(--motion-duration-shell)] ease-[var(--motion-ease-spring)] motion-reduce:duration-[var(--motion-duration-reduced)]',
                view === 'create' && '-translate-x-full rtl:translate-x-full',
              )}
            >
              {/* Inset keeps focus rings inside the clip. */}
              <div
                ref={actionsPaneRef}
                className="w-full shrink-0 px-[var(--space-xxs)]"
                data-vault-pane="actions"
                inert={view !== 'actions'}
              >
                <VaultActions
                  busy={busy}
                  onBrowse={onOpenFolder}
                  onCreateVault={() => show('create')}
                />
              </div>
              <div
                ref={createPaneRef}
                className="w-full shrink-0 px-[var(--space-xxs)]"
                data-vault-pane="create"
                inert={view !== 'create'}
              >
                <VaultCreate
                  busy={busy}
                  onBrowse={onPickFolder}
                  onBack={() => show('actions')}
                  onCreate={onCreateVault}
                />
              </div>
            </div>
          </div>

          {refusal ? (
            <p role="alert" className="text-destructive text-sm">
              {refusal}
            </p>
          ) : null}

          {onAutostartChange ? (
            <label className="text-muted-foreground flex items-center justify-center gap-[var(--space-xs)] text-sm">
              <input
                type="checkbox"
                checked={autostart ?? false}
                onChange={(event) => onAutostartChange(event.target.checked)}
              />
              Launch at login
            </label>
          ) : null}
        </div>
      </div>
    </AppShell>
  )
}
