// The only place the app talks to the host. Cards get three things from here: the tool result
// they were drawn for, a way to send a message as the person (ui/message), and a way to switch
// between the inline card and the full view. Nothing here writes a file or calls a server tool.

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useApp, useHostStyles } from "@modelcontextprotocol/ext-apps/react";
import type { App } from "@modelcontextprotocol/ext-apps/react";

type DisplayMode = "inline" | "fullscreen";

export type ToolResult = { schema?: string } & Record<string, unknown>;

export type CardHost = {
  /** structuredContent of the tool result that mounted this card, once it arrives. */
  result: ToolResult | null;
  displayMode: DisplayMode;
  canFullView: boolean;
  /**
   * Sends text into the conversation as the person's message. `context` travels with it as
   * model context the person doesn't see (ui/update-model-context, sent first; the latest wins),
   * for exact details like a preview's digest that would clutter the visible message.
   */
  send: (text: string, context?: Record<string, unknown>) => Promise<void>;
  requestFullView: () => Promise<void>;
  requestInline: () => Promise<void>;
};

/** Exported for StaticCardHost (bridge/static.tsx); cards read it through useCardHost. */
export const HostContext = createContext<CardHost | null>(null);

export function useCardHost(): CardHost {
  const host = useContext(HostContext);
  if (!host) throw new Error("useCardHost needs a CardHostProvider");
  return host;
}

/** Builds the CardHost for a connected App. Exported for tests, which pass a stand-in App. */
export function cardHost(
  app: App | null,
  result: ToolResult | null,
  displayMode: DisplayMode,
): CardHost {
  const modes = app?.getHostContext()?.availableDisplayModes ?? [];
  return {
    result,
    displayMode,
    canFullView: modes.includes("fullscreen"),
    send: async (text, context) => {
      if (context)
        await app?.updateModelContext({
          content: [{ type: "text", text: JSON.stringify(context) }],
          structuredContent: context,
        });
      await app?.sendMessage({
        role: "user",
        content: [{ type: "text", text }],
      });
    },
    requestFullView: async () => {
      if (modes.includes("fullscreen"))
        await app?.requestDisplayMode({ mode: "fullscreen" });
    },
    requestInline: async () => {
      await app?.requestDisplayMode({ mode: "inline" });
    },
  };
}

export function CardHostProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<ToolResult | null>(null);
  const [displayMode, setDisplayMode] = useState<DisplayMode>("inline");
  const { app } = useApp({
    appInfo: { name: "knowledge-mcp", version: "0.1.0" },
    capabilities: { availableDisplayModes: ["inline", "fullscreen"] },
    autoResize: true,
    onAppCreated: (created) => {
      created.ontoolresult = (params) =>
        setResult((params.structuredContent as ToolResult | undefined) ?? null);
      created.onhostcontextchanged = (params) => {
        if (
          params.displayMode === "inline" ||
          params.displayMode === "fullscreen"
        )
          setDisplayMode(params.displayMode);
      };
    },
  });
  // Theme, Claude's style variables and fonts, re-applied whenever the host context changes.
  useHostStyles(app, app?.getHostContext());
  useEffect(() => {
    const mode = app?.getHostContext()?.displayMode;
    if (mode === "inline" || mode === "fullscreen") setDisplayMode(mode);
  }, [app]);
  const host = useMemo(
    () => cardHost(app, result, displayMode),
    [app, result, displayMode],
  );
  return <HostContext value={host}>{children}</HostContext>;
}
