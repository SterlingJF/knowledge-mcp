// File: launcher/src/component-patterns/VaultActions.tsx

import { Button } from '@/component-elements/button'
import { Card, CardContent } from '@/component-elements/card'
import { Separator } from '@/component-elements/separator'
import { FolderOpen, Plus } from 'lucide-react'

export type VaultActionsProps = {
  busy: boolean
  onBrowse?: () => void
  onCreateVault: () => void
}

type ActionRowProps = {
  title: string
  description: string
  label: string
  icon: typeof FolderOpen
  disabled: boolean
  variant?: 'default' | 'outline'
  isCreate?: boolean
  onClick: () => void
}

function ActionRow({
  title,
  description,
  label,
  icon: Icon,
  disabled,
  variant = 'outline',
  isCreate = false,
  onClick,
}: ActionRowProps) {
  return (
    // minmax(0,1fr) permits long text to shrink.
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-[var(--space-md)]">
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-muted-foreground text-sm">{description}</p>
      </div>
      <Button
        variant={variant}
        size="sm"
        disabled={disabled}
        onClick={onClick}
        data-vault-create={isCreate ? '' : undefined}
      >
        <Icon aria-hidden="true" />
        {label}
      </Button>
    </div>
  )
}

export function VaultActions({
  busy,
  onBrowse,
  onCreateVault,
}: VaultActionsProps) {
  return (
    <Card size="sm" className="w-full">
      <CardContent className="gap-[var(--space-md)]">
        <ActionRow
          title="Create new vault"
          description="Make a new folder and serve it as a vault."
          label="Create"
          icon={Plus}
          disabled={busy}
          variant="default"
          isCreate
          onClick={onCreateVault}
        />
        <Separator />
        <ActionRow
          title="Add existing folder"
          description="Serve a folder you already have. It joins the list."
          label="Add"
          icon={FolderOpen}
          disabled={busy || !onBrowse}
          onClick={() => onBrowse?.()}
        />
      </CardContent>
    </Card>
  )
}
