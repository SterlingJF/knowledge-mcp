// P06 Card lifecycle: a card is live until pressed, then frozen; it is replaced when a younger
// card about the same subject shows up. A press sends the person's message and nothing else.
import { useCallback, useEffect, useRef, useState } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { CardAction, CardState } from "./card-shell";

export const CARD_CHANNEL = "knowledge-mcp";

export type InstanceKey = {
  subject: string;
  /** ISO-8601; compared as a string. */
  created_at?: string;
  seq: number;
};

function isInstanceKey(value: unknown): value is InstanceKey {
  if (typeof value !== "object" || value === null) return false;
  if (!("subject" in value && "seq" in value)) return false;
  const createdAt = "created_at" in value ? value.created_at : undefined;
  return (
    typeof value.subject === "string" &&
    (createdAt === undefined || typeof createdAt === "string") &&
    typeof value.seq === "number"
  );
}

/** True when `a` was made after `b`: later created_at, then higher seq when equal or missing. */
export function isYounger(a: InstanceKey, b: InstanceKey): boolean {
  if (a.created_at && b.created_at && a.created_at !== b.created_at)
    return a.created_at > b.created_at;
  return a.seq > b.seq;
}

export type CardLifecycle = {
  state: CardState;
  frozenLine: string | undefined;
  /**
   * Freezes the card at once and sends the action's message. `extra` is anything the card needs
   * to redraw its frozen look after a remount (e.g. the kept changes); it comes back as `restored`.
   */
  press: (action: CardAction, extra?: unknown) => void;
  /** The `extra` saved with the press, when the card was frozen before this mount. */
  restored?: unknown;
};

// Claude remounts the iframe (and resends the result) when the person switches conversations,
// so a frozen or replaced card is remembered in localStorage, keyed by the result's identity.
const STORE_PREFIX = "km-card:";
const STORE_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;

type Saved = {
  state: "frozen" | "replaced";
  frozenLine?: string;
  extra?: unknown;
  at: number;
};

/** A short, stable FNV-1a hash of the result, for results without an instance key. */
function hash(text: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(36);
}

function isSaved(value: unknown): value is Saved {
  if (typeof value !== "object" || value === null) return false;
  if (!("state" in value && "at" in value)) return false;
  return (
    (value.state === "frozen" || value.state === "replaced") &&
    typeof value.at === "number"
  );
}

function parse(raw: string | null): Saved | null {
  if (raw === null) return null;
  const value: unknown = JSON.parse(raw);
  return isSaved(value) ? value : null;
}

function storeKey(result: unknown): string | null {
  if (result === null || typeof result !== "object") return null;
  const instance = "instance" in result ? result.instance : undefined;
  if (isInstanceKey(instance))
    return `${STORE_PREFIX}${instance.subject}|${instance.created_at ?? ""}|${instance.seq}`;
  try {
    return `${STORE_PREFIX}h${hash(JSON.stringify(result))}`;
  } catch {
    return null;
  }
}

function isStale(saved: Saved | null): boolean {
  return saved === null || Date.now() - saved.at > STORE_MAX_AGE_MS;
}

function load(key: string | null): Saved | null {
  if (!key) return null;
  try {
    const saved = parse(localStorage.getItem(key));
    return isStale(saved) ? null : saved;
  } catch {
    return null;
  }
}

function save(key: string | null, saved: Omit<Saved, "at">) {
  if (!key) return;
  try {
    localStorage.setItem(key, JSON.stringify({ ...saved, at: Date.now() }));
  } catch {
    // Storage blocked or full: the card still works for this mount.
  }
}

/** Drops entries older than about 30 days, or unreadable, so storage never grows without bound. */
function sweep() {
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (!k?.startsWith(STORE_PREFIX)) continue;
      let stale = true;
      try {
        stale = isStale(parse(localStorage.getItem(k)));
      } catch {
        // Unreadable: drop it.
      }
      if (stale) localStorage.removeItem(k);
    }
  } catch {
    // Storage blocked: nothing to sweep.
  }
}

type Snapshot = {
  key: string | null;
  frozenLine: string | undefined;
  replaced: boolean;
  extra: unknown;
};

function snapshot(key: string | null): Snapshot {
  const saved = load(key);
  return {
    key,
    frozenLine: saved?.state === "frozen" ? saved.frozenLine : undefined,
    replaced: saved?.state === "replaced",
    extra: saved?.extra,
  };
}

/**
 * The card's own state, restored from storage during render (never in an effect), so a frozen
 * card is never painted live; restored again if the result's identity changes.
 */
function useSnapshot(key: string | null) {
  const [snap, setSnap] = useState(() => snapshot(key));
  const current = snap.key === key ? snap : snapshot(key);
  if (current !== snap) setSnap(current);
  useEffect(sweep, []);
  return [current, setSnap] as const;
}

/** Stands the card down when a younger card about the same subject appears. */
function useSupersession(result: unknown, onReplaced: () => void) {
  const instance =
    typeof result === "object" && result !== null && "instance" in result
      ? result.instance
      : undefined;
  const id = isInstanceKey(instance) ? instance : null;
  const subject = id?.subject;
  const createdAt = id?.created_at;
  const seq = id?.seq;
  const replacedRef = useRef(onReplaced);
  replacedRef.current = onReplaced;

  useEffect(() => {
    if (subject === undefined || seq === undefined) return;
    if (typeof BroadcastChannel === "undefined") return;
    const own: InstanceKey = { subject, created_at: createdAt, seq };
    const channel = new BroadcastChannel(CARD_CHANNEL);
    channel.onmessage = (event: MessageEvent) => {
      const heard: unknown = event.data;
      if (!isInstanceKey(heard) || heard.subject !== own.subject) return;
      if (isYounger(heard, own)) replacedRef.current();
      // An older card mounted after this one: tell it this one exists.
      else if (isYounger(own, heard)) channel.postMessage(own);
    };
    channel.postMessage(own);
    return () => channel.close();
  }, [subject, createdAt, seq]);
}

/** Call it in the card, not in SummaryCard or FullView, so state survives the display-mode switch. */
export function useCardLifecycle(): CardLifecycle {
  const host = useCardHost();
  const key = storeKey(host.result);
  const [snap, setSnap] = useSnapshot(key);
  const { frozenLine, replaced } = snap;

  useSupersession(host.result, () =>
    setSnap((was) => {
      // A pressed card keeps its frozen line; only a live card stands down.
      if (was.frozenLine === undefined && !was.replaced)
        save(was.key, { state: "replaced" });
      return { ...was, replaced: true };
    }),
  );

  // Blocks a second press in the same tick, before the frozen state renders.
  const pressedFor = useRef<string | null | undefined>(undefined);
  const send = host.send;
  const press = useCallback(
    (action: CardAction, extra?: unknown) => {
      if (frozenLine !== undefined || replaced || action.disabled) return;
      if (pressedFor.current === key) return;
      pressedFor.current = key;
      setSnap({ key, frozenLine: action.frozenLine, replaced, extra });
      save(key, { state: "frozen", frozenLine: action.frozenLine, extra });
      void send(action.message, action.context);
    },
    [send, frozenLine, replaced, key, setSnap],
  );

  const state: CardState =
    frozenLine !== undefined ? "frozen" : replaced ? "replaced" : "live";
  return { state, frozenLine, press, restored: snap.extra };
}

/** The four shell props every card wires from its lifecycle. */
export function lifecycleProps(lifecycle: CardLifecycle) {
  return {
    state: lifecycle.state,
    frozenLine: lifecycle.frozenLine,
    onAction: lifecycle.press,
  };
}
