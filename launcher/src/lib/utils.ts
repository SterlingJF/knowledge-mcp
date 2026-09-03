// File: launcher/src/lib/utils.ts
//

import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

import type { ClassValue } from 'clsx'

export function cn(...inputs: Array<ClassValue>) {
  return twMerge(clsx(inputs))
}

export function entriesOf<const T extends Record<string, unknown>>(obj: T) {
  return Object.entries(obj) as Array<{ [K in keyof T]: [K, T[K]] }[keyof T]>
}

/** Object keys as a readonly non-empty tuple, accepted by z.enum(). */
export function keysTupleOf<const T extends Record<string, unknown>>(obj: T) {
  const keys = Object.keys(obj) as Array<keyof T>
  if (keys.length === 0) throw new Error('keysTupleOf received an empty object')
  return keys as unknown as readonly [keyof T, ...Array<keyof T>]
}
