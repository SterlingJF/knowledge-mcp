// The only place the app talks to the host. Cards get three things from here: the tool result
// they were drawn for, a way to send a message as the person (ui/message), and a way to switch
// between the inline card and the full view. Nothing here writes a file or calls a server tool.

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useApp, useHostStyles } from "@modelcontextprotocol/ext-apps/react";
import type { App } from "@modelcontextprotocol/ext-apps/react";

type DisplayMode = "inline" | "fullscreen";

/** hostContext.safeAreaInsets, in px. */
export type SafeAreaInsets = {
  top: number;
  right: number;
  bottom: number;
  left: number;
};

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
  /** The host's safe area; HostRoot pads the app root by it. */
  safeAreaInsets?: SafeAreaInsets;
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
  safeAreaInsets?: SafeAreaInsets,
): CardHost {
  const modes = app?.getHostContext()?.availableDisplayModes ?? [];
  return {
    result,
    safeAreaInsets,
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

const SIDES = ["top", "right", "bottom", "left"] as const;

/**
 * The app root: padded by the host's safe area so nothing sits under a notch or home bar.
 * The insets go on <html> beside the host's style variables; styles.css pads the root by them.
 */
export function HostRoot({ children }: { children: ReactNode }) {
  const insets = useCardHost().safeAreaInsets;
  useEffect(() => {
    const style = document.documentElement.style;
    for (const side of SIDES)
      if (insets) style.setProperty(`--safe-area-${side}`, `${insets[side]}px`);
      else style.removeProperty(`--safe-area-${side}`);
  }, [insets]);
  return <div data-app-root="">{children}</div>;
}

export function CardHostProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<ToolResult | null>(null);
  // What the host changed since connecting; until then its first context answers.
  const [changedMode, setDisplayMode] = useState<DisplayMode>();
  const [changedInsets, setInsets] = useState<SafeAreaInsets>();
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
        if (params.safeAreaInsets) setInsets(params.safeAreaInsets);
      };
    },
  });
  // Theme, Claude's style variables and fonts, re-applied whenever the host context changes.
  const context = app?.getHostContext();
  useHostStyles(app, context);
  const firstMode = context?.displayMode;
  const displayMode =
    changedMode ??
    (firstMode === "inline" || firstMode === "fullscreen"
      ? firstMode
      : "inline");
  const insets = changedInsets ?? context?.safeAreaInsets;
  const host = useMemo(
    () => cardHost(app, result, displayMode, insets),
    [app, result, displayMode, insets],
  );
  return (
    <HostContext value={host}>
      <HostRoot>{children}</HostRoot>
    </HostContext>
  );
}
