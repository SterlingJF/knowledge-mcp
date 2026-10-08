// File: launcher/src/lib/backend.ts

import type { ProcessStatus } from '@/lib/shell'
import type { Vault } from 'components/lib/types'

export type { Vault }

const DEVELOPMENT_ORIGIN =
  (import.meta.env.VITE_KM_BACKEND_ORIGIN as string | undefined) ??
  'http://127.0.0.1:17951'

const API_PREFIX = '/api/v1'

export const apiBaseUrlFor = (origin: string): string =>
  `${origin}${API_PREFIX}`

export const developmentOrigin = (): string => DEVELOPMENT_ORIGIN

export const originFromStatus = (status: ProcessStatus): string =>
  `http://127.0.0.1:${status.port}`

/** /ready payload outside contracts/project/v1. */
export type Readiness = {
  status: string
  role: string
  storageRoot: string | null
  storageReady: boolean
  storageDetail: string | null
  universesLoaded: number
}

export type StorageOption = {
  type: string
  label: string
}

/** Desktop-only /storage payload outside contracts/project/v1. */
export type Storage = {
  storageRoot: string | null
  storageName: string | null
  storageReady: boolean
  storageDetail: string | null
  options: Array<StorageOption>
  vaults: Array<Vault>
}

export class BackendUnreachable extends Error {}

/** Vault id for X-Km-Vault. Null: engine default. */
let pinnedVaultId: string | null = null

export const setVaultId = (id: string | null): void => {
  pinnedVaultId = id
}

const vaultHeaders = (): Record<string, string> =>
  pinnedVaultId ? { 'X-Km-Vault': pinnedVaultId } : {}

export const fetchReadiness = async (origin: string): Promise<Readiness> => {
  let response: Response
  try {
    response = await fetch(`${origin}/ready`, { headers: vaultHeaders() })
  } catch (cause) {
    throw new BackendUnreachable(
      `Nothing answered at ${origin}. The backend is not running, or it is on another port.`,
      { cause },
    )
  }

  // Not-ready answers 503 with the same body.
  if (response.status !== 200 && response.status !== 503) {
    throw new BackendUnreachable(
      `${origin} answered ${response.status}, which is not a readiness reply.`,
    )
  }

  return (await response.json()) as Readiness
}

const storageReply = async (
  origin: string,
  response: Response,
  // A refused folder answers 422 with the same body and the reason in storageDetail.
  acceptable: ReadonlyArray<number>,
): Promise<Storage> => {
  if (!acceptable.includes(response.status)) {
    throw new BackendUnreachable(
      `${origin} answered ${response.status}, which is not a storage reply.`,
    )
  }
  const body = (await response.json()) as Omit<Storage, 'vaults'> & {
    vaults?: Array<Vault>
  }
  return { ...body, vaults: body.vaults ?? [] }
}

export const fetchStorage = async (origin: string): Promise<Storage> => {
  let response: Response
  try {
    response = await fetch(`${origin}/storage`, { headers: vaultHeaders() })
  } catch (cause) {
    throw new BackendUnreachable(
      `Nothing answered at ${origin}. The backend is not running, or it is on another port.`,
      { cause },
    )
  }
  return storageReply(origin, response, [200])
}

const sendStorage = async (
  origin: string,
  path: string,
  method: 'PUT' | 'POST' | 'PATCH' | 'DELETE',
  body?: unknown,
): Promise<Storage> => {
  let response: Response
  try {
    response = await fetch(`${origin}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...vaultHeaders() },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (cause) {
    throw new BackendUnreachable(
      `Nothing answered at ${origin}. The backend is not running, or it is on another port.`,
      { cause },
    )
  }
  return storageReply(origin, response, [200, 422])
}

export const setStorage = async (
  origin: string,
  path: string,
): Promise<Storage> => sendStorage(origin, '/storage', 'PUT', { path })

export const createVault = async (
  origin: string,
  parent: string,
  name: string,
): Promise<Storage> =>
  sendStorage(origin, '/storage/vaults', 'POST', { parent, name })

/** Vault id remains unchanged (server/app/routers/storage.py). */
export const changeVault = async (
  origin: string,
  vaultId: string,
  change: { name?: string; parent?: string },
): Promise<Storage> =>
  sendStorage(origin, `/storage/vaults/${vaultId}`, 'PATCH', change)

/** Does not touch vault folder (server/app/routers/storage.py). */
export const removeVault = async (
  origin: string,
  vaultId: string,
): Promise<Storage> =>
  sendStorage(origin, `/storage/vaults/${vaultId}`, 'DELETE')
