// File: launcher/src/component-patterns/VaultCreate.tsx

import { Input } from '@/component-core/input'
import { Button } from '@/component-elements/button'
import { Card, CardContent } from '@/component-elements/card'
import { Separator } from '@/component-elements/separator'
import { errorOf, requiredMessage } from '@/component-patterns/vaultForm'
import { useAppForm } from '@/lib/formFactory'
import { ArrowLeft, FolderOpen } from 'lucide-react'
import { useId } from 'react'

import type { ReactNode } from 'react'

export type VaultCreateProps = {
  busy: boolean
  onBrowse?: () => Promise<string | null>
  onBack: () => void
  onCreate: (parent: string, name: string) => Promise<boolean>
}

type FieldRowIds = { control: string; title: string; error: string }

type FieldRowProps = {
  title: string
  description: string
  hint?: string
  error: string | null
  /** False for the Browse button. A label overrides its accessible name. */
  labels: boolean
  children: (ids: FieldRowIds) => ReactNode
}

/** Adds `aria-invalid` and `aria-describedby` (formFactory). */
function FieldRow({
  title,
  description,
  hint,
  error,
  labels,
  children,
}: FieldRowProps) {
  const ids: FieldRowIds = {
    control: useId(),
    title: useId(),
    error: useId(),
  }
  const heading = labels ? (
    <label htmlFor={ids.control} className="text-sm font-medium">
      {title}
    </label>
  ) : (
    <p id={ids.title} className="text-sm font-medium">
      {title}
    </p>
  )

  return (
    // minmax(0,1fr) permits long paths to shrink.
    <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-[var(--space-md)]">
      <div className="min-w-0 space-y-0.5">
        {heading}
        <p className="text-muted-foreground text-sm">{description}</p>
        {hint ? (
          // break-all handles unbroken path segments.
          <p className="text-foreground text-sm font-medium break-all">
            {hint}
          </p>
        ) : null}
        {error ? (
          <p id={ids.error} className="text-destructive text-sm">
            {error}
          </p>
        ) : null}
      </div>
      {children(ids)}
    </div>
  )
}

/** Validates only emptiness. Other checks are in server/app/routers/storage.py. */
export function VaultCreate({
  busy,
  onBrowse,
  onBack,
  onCreate,
}: VaultCreateProps) {
  const form = useAppForm({
    defaultValues: { name: '', location: '' },
    onSubmit: async ({ value }) => {
      const made = await onCreate(value.location.trim(), value.name.trim())
      if (made) form.reset()
    },
  })

  return (
    <form
      className="w-full space-y-[var(--space-lg)]"
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
    >
      <div className="space-y-[var(--space-sm)]">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="-ml-[var(--space-sm)]"
          onClick={onBack}
        >
          <ArrowLeft aria-hidden="true" />
          Back
        </Button>
        <h2 className="text-sm font-medium">Create local vault</h2>
      </div>

      <Card size="sm">
        <CardContent className="gap-[var(--space-md)]">
          <form.AppField
            name="name"
            validators={{
              onChange: ({ value }) => requiredMessage(value, 'Give it a name'),
            }}
          >
            {(field) => {
              const error = errorOf(field.state.meta)
              return (
                <FieldRow
                  title="Vault name"
                  description="The folder is created with this name."
                  error={error}
                  labels
                >
                  {(ids) => (
                    <Input
                      id={ids.control}
                      name={field.name}
                      className="w-52"
                      placeholder="Vault name"
                      value={field.state.value}
                      aria-invalid={error ? true : undefined}
                      aria-describedby={error ? ids.error : undefined}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      onBlur={field.handleBlur}
                    />
                  )}
                </FieldRow>
              )
            }}
          </form.AppField>

          <Separator />

          <form.AppField
            name="location"
            validators={{
              onChange: ({ value }) =>
                requiredMessage(value, 'Pick where it goes'),
            }}
          >
            {(field) => {
              const error = errorOf(field.state.meta)
              return (
                <FieldRow
                  title="Location"
                  description={
                    field.state.value
                      ? 'Your new vault will be placed in:'
                      : 'Pick a place to put your new vault.'
                  }
                  hint={onBrowse ? field.state.value : undefined}
                  error={error}
                  labels={onBrowse === undefined}
                >
                  {(ids) =>
                    onBrowse ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        aria-describedby={ids.title}
                        onClick={() => {
                          void onBrowse().then((chosen) => {
                            if (chosen) field.handleChange(chosen)
                          })
                        }}
                      >
                        <FolderOpen aria-hidden="true" />
                        Browse
                      </Button>
                    ) : (
                      <Input
                        id={ids.control}
                        name={field.name}
                        className="w-52"
                        placeholder="/Users/you/vaults"
                        value={field.state.value}
                        aria-invalid={error ? true : undefined}
                        aria-describedby={error ? ids.error : undefined}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                        onBlur={field.handleBlur}
                      />
                    )
                  }
                </FieldRow>
              )
            }}
          </form.AppField>
        </CardContent>
      </Card>

      {/* Boolean selector avoids fresh-object inequality. canSubmit starts true before onChange runs. */}
      <form.Subscribe
        selector={(state) =>
          state.canSubmit &&
          state.values.name.trim() !== '' &&
          state.values.location.trim() !== ''
        }
      >
        {(ready) => (
          <div className="flex justify-center">
            <Button type="submit" size="sm" disabled={busy || !ready}>
              {busy ? 'Creating…' : 'Create'}
            </Button>
          </div>
        )}
      </form.Subscribe>
    </form>
  )
}
