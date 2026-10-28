// A stand-in host for tests and the gallery: cards render inside it exactly as inside the real
// provider, and it records what they asked the host to do instead of reaching a harness.

import type { ReactNode } from "react";

import { HostContext } from "./bridge";
import type { CardHost, ToolResult } from "./bridge";

export type RecordedHost = CardHost & {
  /** Messages the card sent, in order. */
  sent: Array<string>;
  /** Display modes the card asked for, in order. */
  requested: Array<"inline" | "fullscreen">;
};

export function stubCardHost(
  options: {
    result?: ToolResult | null;
    displayMode?: "inline" | "fullscreen";
    canFullView?: boolean;
  } = {},
): RecordedHost {
  const sent: Array<string> = [];
  const requested: Array<"inline" | "fullscreen"> = [];
  return {
    result: options.result ?? null,
    displayMode: options.displayMode ?? "inline",
    canFullView: options.canFullView ?? true,
    sent,
    requested,
    send: async (text) => {
      sent.push(text);
    },
    requestFullView: async () => {
      requested.push("fullscreen");
    },
    requestInline: async () => {
      requested.push("inline");
    },
  };
}

export function StaticCardHost({
  host,
  children,
}: {
  host: CardHost;
  children: ReactNode;
}) {
  return <HostContext value={host}>{children}</HostContext>;
}
