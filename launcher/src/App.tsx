// File: launcher/src/App.tsx

import {
  BackendUnreachable,
  changeVault,
  createVault,
  developmentOrigin,
  removeVault,
  fetchReadiness,
  fetchStorage,
  originFromStatus,
  setStorage as putStorage,
} from '@/lib/backend'
import {
  BACKEND_PROCESS,
  announceWindowReady,
  autostartEnabled,
  isHostedByShell,
  onProcessStatus,
  pickStorageFolder,
  revealVault,
  setAutostart,
} from '@/lib/shell'
import { DirectionProvider } from 'components/component-core/direction'
import { toast } from 'components/component-core/toast'
import { TooltipProvider } from 'components/component-core/tooltip'
import { Toaster } from 'components/component-elements/toaster'
import { BackendUnreachableNotice } from 'components/component-patterns/BackendUnreachableNotice'
import { ThemeProvider } from 'components/component-patterns/ThemeProvider'
import { VaultSwitcher } from 'components/component-patterns/VaultSwitcher'
import { useCallback, useEffect, useRef, useState } from 'react'

import type { Readiness, Storage, Vault } from '@/lib/backend'
import type { VaultAction } from 'components/component-patterns/VaultRowMenu'

type Connection =
  | { phase: 'waiting' }
  | { phase: 'ready'; readiness: Readiness }
  | { phase: 'no-store'; readiness: Readiness }
  | { phase: 'unreachable'; message: string }

export function App() {
  const [connection, setConnection] = useState<Connection>({ phase: 'waiting' })
  const [origin, setOrigin] = useState<string | null>(null)
  const originRef = useRef<string | null>(null)
  const [storage, setStorage] = useState<Storage | null>(null)
  const [refusal, setRefusal] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [autostart, setAutostartState] = useState(false)
  const [direction, setDirection] = useState<'ltr' | 'rtl'>(() =>
    document.documentElement.dir === 'rtl' ? 'rtl' : 'ltr',
  )

  useEffect(() => {
    if (!isHostedByShell()) return
    let cancelled = false
    void autostartEnabled().then((enabled) => {
      if (!cancelled) setAutostartState(enabled)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const changeAutostart = useCallback(async (enabled: boolean) => {
    try {
      await setAutostart(enabled)
      setAutostartState(enabled)
    } catch {
      setRefusal('Launch at login could not be changed.')
    }
  }, [])

  useEffect(() => {
    const root = document.documentElement
    const observer = new MutationObserver(() => {
      setDirection(root.dir === 'rtl' ? 'rtl' : 'ltr')
    })
    observer.observe(root, { attributeFilter: ['dir'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let cancelled = false
    let unlisten: (() => void) | undefined

    const connect = async (at: string) => {
      originRef.current = at
      setOrigin(at)
      try {
        const readiness = await fetchReadiness(at)
        const current = await fetchStorage(at)
        if (cancelled) return
        setStorage(current)
        setConnection(
          readiness.storageReady
            ? { phase: 'ready', readiness }
            : { phase: 'no-store', readiness },
        )
      } catch (error) {
        if (cancelled) return
        const message =
          error instanceof BackendUnreachable
            ? error.message
            : 'The backend could not be reached.'
        setConnection({ phase: 'unreachable', message })
      }
    }

    const start = async () => {
      if (!isHostedByShell()) {
        await connect(developmentOrigin())
        return
      }

      unlisten = await onProcessStatus((status) => {
        if (status.name !== BACKEND_PROCESS) return
        if (status.state === 'listening') void connect(originFromStatus(status))
      })
      await announceWindowReady()
    }

    void start()

    return () => {
      cancelled = true
      unlisten?.()
    }
  }, [])

  const applied = useCallback(
    async (result: Storage) => {
      setStorage(result)
      if (!result.storageReady) {
        setRefusal(result.storageDetail ?? 'That folder cannot be used.')
        return
      }
      setRefusal(null)
      if (origin) {
        setConnection({
          phase: 'ready',
          readiness: await fetchReadiness(origin),
        })
      }
    },
    [origin],
  )

  const guarded = useCallback(
    async (work: () => Promise<Storage>): Promise<Storage | null> => {
      if (!origin) return null
      setBusy(true)
      setRefusal(null)
      try {
        const result = await work()
        await applied(result)
        return result
      } catch (error) {
        setRefusal(
          error instanceof BackendUnreachable
            ? error.message
            : 'The vault could not be added.',
        )
        return null
      } finally {
        setBusy(false)
      }
    },
    [applied, origin],
  )

  const addVault = useCallback(
    (path: string) => void guarded(() => putStorage(origin ?? '', path)),
    [guarded, origin],
  )

  const openFolder = useCallback(async () => {
    try {
      const chosen = await pickStorageFolder()
      if (chosen) addVault(chosen)
    } catch {
      setRefusal('The folder picker could not be opened.')
    }
  }, [addVault])

  const makeVault = useCallback(
    async (parent: string, name: string) => {
      const result = await guarded(() =>
        createVault(origin ?? '', parent, name),
      )
      return result?.storageReady === true
    },
    [guarded, origin],
  )

  const renameVault = useCallback(
    async (vault: Vault, name: string) => {
      const result = await guarded(() =>
        changeVault(origin ?? '', vault.id, { name }),
      )
      const took = result?.storageReady === true
      if (took) toast.add({ title: 'Successfully renamed vault.' })
      return took
    },
    [guarded, origin],
  )

  const moveVault = useCallback(
    async (vault: Vault) => {
      try {
        const parent = await pickStorageFolder()
        if (!parent) return
        const result = await guarded(() =>
          changeVault(origin ?? '', vault.id, { parent }),
        )
        if (result?.storageReady === true) {
          toast.add({ title: 'Successfully moved vault.' })
        }
      } catch {
        setRefusal('The folder picker could not be opened.')
      }
    },
    [guarded, origin],
  )

  const onVaultAction = useCallback(
    (action: VaultAction, vault: Vault) => {
      switch (action) {
        case 'copy-id': {
          // Clipboard may be absent outside a secure context.
          const clipboard = navigator.clipboard as Clipboard | undefined
          if (!clipboard) {
            setRefusal('This build cannot reach the clipboard.')
            return
          }
          void clipboard.writeText(vault.id)
          setRefusal(null)
          return
        }
        case 'reveal':
          void revealVault(vault.path)
          return
        case 'remove':
          void guarded(() => removeVault(origin ?? '', vault.id))
          return
        // Rename action handled in VaultList.
        case 'rename':
          return
        case 'move':
          void moveVault(vault)
          return
      }
    },
    [guarded, moveVault, origin],
  )

  const surface = () =>
    connection.phase === 'unreachable' ? (
      <BackendUnreachableNotice message={connection.message} />
    ) : (
      <VaultSwitcher
        vaults={storage?.vaults ?? []}
        version={__KM_VERSION__}
        busy={busy}
        refusal={refusal}
        onOpenFolder={isHostedByShell() ? () => void openFolder() : undefined}
        // Picked path becomes the create form's parent.
        onPickFolder={isHostedByShell() ? pickStorageFolder : undefined}
        onCreateVault={makeVault}
        onVaultAction={onVaultAction}
        onRenameVault={renameVault}
        autostart={autostart}
        onAutostartChange={
          isHostedByShell()
            ? (enabled) => void changeAutostart(enabled)
            : undefined
        }
      />
    )

  return (
    <DirectionProvider direction={direction}>
      <TooltipProvider>
        <ThemeProvider defaultTheme="system" storageKey="knowledge-mcp-theme">
          {/* Theme class sits on documentElement. Toast portal inherits it. */}
          <Toaster>{surface()}</Toaster>
        </ThemeProvider>
      </TooltipProvider>
    </DirectionProvider>
  )
}
