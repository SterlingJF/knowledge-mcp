import {
  BackendUnreachable,
  apiBaseUrlFor,
  fetchStorage,
  originFromStatus,
  setStorage,
} from '@/lib/backend'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Storage } from '@/lib/backend'

const ORIGIN = 'http://127.0.0.1:17951'

const STORAGE: Storage = {
  storageRoot: '/Users/sterling/knowledge-mcp',
  storageName: 'knowledge-mcp',
  storageReady: true,
  storageDetail: null,
  options: [{ type: 'filesystem', label: 'A folder on this computer' }],
  vaults: [],
}

const answerWith = (status: number, body: unknown) =>
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

describe('backend origins', () => {
  it('builds the generated client base URL from the backend origin', () => {
    expect(apiBaseUrlFor('http://127.0.0.1:17951')).toBe(
      'http://127.0.0.1:17951/api/v1',
    )
  })

  it('uses the loopback port reported by the native shell', () => {
    expect(
      originFromStatus({
        name: 'km-server',
        port: 17951,
        pid: 42,
        state: 'listening',
        detail: 'Accepting connections.',
      }),
    ).toBe('http://127.0.0.1:17951')
  })
})

describe('storage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reads a reply with no vaults as an empty list', async () => {
    const { vaults: _omitted, ...withoutVaults } = STORAGE
    answerWith(200, withoutVaults)

    await expect(fetchStorage(ORIGIN)).resolves.toEqual({
      ...withoutVaults,
      vaults: [],
    })
  })

  it('reads the current storage state', async () => {
    answerWith(200, STORAGE)

    await expect(fetchStorage(ORIGIN)).resolves.toEqual(STORAGE)
  })

  it('sends the chosen path as a PUT', async () => {
    const fetchSpy = answerWith(200, STORAGE)

    await setStorage(ORIGIN, '/Users/sterling/knowledge-mcp')

    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(`${ORIGIN}/storage`)
    expect(init.method).toBe('PUT')
    expect(init.body).toBe(
      JSON.stringify({ path: '/Users/sterling/knowledge-mcp' }),
    )
  })

  it('treats a refused folder as an answer, not a failure', async () => {
    const refused = {
      ...STORAGE,
      storageReady: false,
      storageDetail: 'Storage root does not exist: /nowhere',
    }
    answerWith(422, refused)

    await expect(setStorage(ORIGIN, '/nowhere')).resolves.toEqual(refused)
  })

  it('refuses to read an unexpected status as a storage reply', async () => {
    answerWith(500, { detail: 'boom' })

    await expect(fetchStorage(ORIGIN)).rejects.toBeInstanceOf(
      BackendUnreachable,
    )
  })

  it('reports an unreachable backend when nothing answers', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('refused'))

    await expect(setStorage(ORIGIN, '/anywhere')).rejects.toBeInstanceOf(
      BackendUnreachable,
    )
  })
})
