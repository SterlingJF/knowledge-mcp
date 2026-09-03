// File: launcher/src/lib/shell.ts
//
// Native shell emits process-status. Window emits ui-ready and reveal-vault.

import type { UnlistenFn } from '@tauri-apps/api/event'

export const BACKEND_PROCESS = 'km-server'

/** process-status payload (src-tauri/src/lib.rs). */
export type ProcessStatus = {
  name: string
  port: number
  pid: number | null
  state: 'spawned' | 'listening' | 'occupied' | 'timeout' | 'exited'
  detail: string
}

export const isHostedByShell = (): boolean =>
  typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

// Lazy: import fails in a plain browser.
const eventApi = async () => import('@tauri-apps/api/event')

export const onProcessStatus = async (
  handler: (status: ProcessStatus) => void,
): Promise<UnlistenFn> => {
  const { listen } = await eventApi()
  return listen<ProcessStatus>('process-status', (event) =>
    handler(event.payload),
  )
}

// process-log is unconsumed here. Native shell prints each line (src-tauri/src/lib.rs).

/** Requests status replay (src-tauri/src/lib.rs). */
export const announceWindowReady = async (): Promise<void> => {
  const { emit } = await eventApi()
  await emit('ui-ready')
}

export const revealVault = async (path: string): Promise<void> => {
  const { emit } = await eventApi()
  await emit('reveal-vault', { path })
}

// Dialog returns selected path only. Backend handles vault storage operations.
const dialogApi = async () => import('@tauri-apps/plugin-dialog')

/** Native folder picker. Null when the person cancels. */
export const pickStorageFolder = async (): Promise<string | null> => {
  const { open } = await dialogApi()
  const chosen = await open({ directory: true, multiple: false })
  return typeof chosen === 'string' ? chosen : null
}

// LaunchAgent toggle (src-tauri/src/lib.rs, capabilities/default.json).
const autostartApi = async () => import('@tauri-apps/plugin-autostart')

export const autostartEnabled = async (): Promise<boolean> => {
  const { isEnabled } = await autostartApi()
  return isEnabled()
}

export const setAutostart = async (enabled: boolean): Promise<void> => {
  const { enable, disable } = await autostartApi()
  await (enabled ? enable() : disable())
}
