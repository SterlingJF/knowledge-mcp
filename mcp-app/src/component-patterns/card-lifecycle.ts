// P06 Card lifecycle: a card is live until pressed, then frozen; it is replaced when a younger
// card about the same subject shows up. A press sends the person's message and nothing else.
import { useCallback, useEffect, useRef, useState } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { CardAction, CardState } from "./card-shell";

export const CARD_CHANNEL = "knowledge-mcp";

export type InstanceKey = {
  subject: string;
  created_at: string | number;
  seq: number;
};

function isInstanceKey(value: unknown): value is InstanceKey {
  if (typeof value !== "object" || value === null) return false;
  if (!("subject" in value && "created_at" in value && "seq" in value))
    return false;
  return (
    typeof value.subject === "string" &&
    (typeof value.created_at === "string" ||
      typeof value.created_at === "number") &&
    typeof value.seq === "number"
  );
}

/** True when `a` was made after `b`: later created_at, then higher seq. */
export function isYounger(a: InstanceKey, b: InstanceKey): boolean {
  if (a.created_at !== b.created_at) return a.created_at > b.created_at;
  return a.seq > b.seq;
}

export type CardLifecycle = {
  state: CardState;
  frozenLine: string | undefined;
  /** Freezes the card at once and sends the action's message. */
  press: (action: CardAction) => void;
};

/** Call it in the card, not in SummaryCard or FullView, so state survives the display-mode switch. */
export function useCardLifecycle(): CardLifecycle {
  const host = useCardHost();
  const [frozenLine, setFrozenLine] = useState<string>();
  const [replaced, setReplaced] = useState(false);
  const pressed = useRef(false);

  const instance = host.result?.instance;
  const key = isInstanceKey(instance) ? instance : null;
  const subject = key?.subject;
  const createdAt = key?.created_at;
  const seq = key?.seq;

  useEffect(() => {
    if (subject === undefined || createdAt === undefined || seq === undefined)
      return;
    if (typeof BroadcastChannel === "undefined") return;
    const own: InstanceKey = { subject, created_at: createdAt, seq };
    const channel = new BroadcastChannel(CARD_CHANNEL);
    channel.onmessage = (event: MessageEvent) => {
      const heard: unknown = event.data;
      if (!isInstanceKey(heard) || heard.subject !== own.subject) return;
      if (isYounger(heard, own)) setReplaced(true);
      // An older card mounted after this one: tell it this one exists.
      else if (isYounger(own, heard)) channel.postMessage(own);
    };
    channel.postMessage(own);
    return () => channel.close();
  }, [subject, createdAt, seq]);

  const send = host.send;
  const press = useCallback(
    (action: CardAction) => {
      if (pressed.current) return;
      pressed.current = true;
      setFrozenLine(action.frozenLine);
      void send(action.message);
    },
    [send],
  );

  const state: CardState = replaced
    ? "replaced"
    : frozenLine !== undefined
      ? "frozen"
      : "live";
  return { state, frozenLine, press };
}
