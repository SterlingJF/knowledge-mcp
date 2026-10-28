// Test double for the bridge: tests swap `@/bridge/bridge` for this module and render cards
// inside StubHost, which hands them a CardHost that records what they asked for.
import { createContext, useContext } from "react";
import type { ReactNode } from "react";

import type { CardHost, ToolResult } from "@/bridge/bridge";

const StubContext = createContext<CardHost | null>(null);

export function useCardHost(): CardHost {
  const host = useContext(StubContext);
  if (!host) throw new Error("useCardHost needs a StubHost");
  return host;
}

export type StubRecord = { sent: string[]; requests: string[] };

export function stubHost(
  overrides: Partial<CardHost> = {},
  result: ToolResult | null = null,
): CardHost & StubRecord {
  const sent: string[] = [];
  const requests: string[] = [];
  return {
    result,
    displayMode: "inline",
    canFullView: true,
    send: async (text) => {
      sent.push(text);
    },
    requestFullView: async () => {
      requests.push("fullscreen");
    },
    requestInline: async () => {
      requests.push("inline");
    },
    ...overrides,
    sent,
    requests,
  };
}

export function StubHost({
  host,
  children,
}: {
  host: CardHost;
  children: ReactNode;
}) {
  return <StubContext value={host}>{children}</StubContext>;
}
