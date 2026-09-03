// File: launcher/src/component-patterns/vaultForm.ts
//

export const requiredMessage = (value: string, message: string) =>
  value.trim() ? undefined : message

/** `String()` converts first validator issue to text. */
export const errorOf = (meta: {
  isTouched: boolean
  isValid: boolean
  errors: Array<unknown>
}) =>
  meta.isTouched && !meta.isValid ? String(meta.errors[0] ?? '') || null : null
