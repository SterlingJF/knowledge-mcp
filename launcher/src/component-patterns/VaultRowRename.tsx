// File: launcher/src/component-patterns/VaultRowRename.tsx

import { Input } from '@/component-core/input'
import { errorOf, requiredMessage } from '@/component-patterns/vaultForm'
import { useAppForm } from '@/lib/formFactory'
import { useEffect, useRef } from 'react'

export type VaultRowRenameProps = {
  name: string
  busy: boolean
  onSubmit: (name: string) => Promise<boolean>
  onCancel: () => void
}

export function VaultRowRename({
  name,
  busy,
  onSubmit,
  onCancel,
}: VaultRowRenameProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  const form = useAppForm({
    defaultValues: { name },
    onSubmit: async ({ value }) => {
      const next = value.name.trim()
      if (next === name) {
        onCancel()
        return
      }
      await onSubmit(next)
    },
  })

  useEffect(() => {
    const input = inputRef.current
    if (!input) return
    input.focus()
    input.select()
  }, [])

  return (
    <form
      className="w-full"
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
    >
      <form.AppField
        name="name"
        validators={{
          onChange: ({ value }) =>
            requiredMessage(value, 'A vault needs a name'),
        }}
      >
        {(field) => {
          const error = errorOf(field.state.meta)
          return (
            <>
              <Input
                ref={inputRef}
                name={field.name}
                aria-label={`Rename ${name}`}
                aria-invalid={error ? true : undefined}
                className="h-7 w-full text-sm"
                disabled={busy}
                value={field.state.value}
                onChange={(event) => field.handleChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== 'Escape') return
                  event.preventDefault()
                  onCancel()
                }}
                onBlur={() => {
                  field.handleBlur()
                  void form.handleSubmit()
                }}
              />
              {error ? (
                <p className="text-destructive pt-0.5 text-xs">{error}</p>
              ) : null}
            </>
          )
        }}
      </form.AppField>
    </form>
  )
}
