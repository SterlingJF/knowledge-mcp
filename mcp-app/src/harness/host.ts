// Host side of the harness: what Claude does for one app iframe, minus the chat.
// Kept free of the DOM so the Vitest test can drive it against a real App over linked transports.

import { AppBridge } from "@modelcontextprotocol/ext-apps/app-bridge";
import type {
  McpUiDisplayMode,
  McpUiHostContext,
  McpUiStyles,
} from "@modelcontextprotocol/ext-apps/app-bridge";

import kmtokens from "../../../design/mcp-app/kmtokens.js?raw";

export type Theme = "light" | "dark";

/** The `"--name": "value"` pairs inside one `name: { ... }` block of kmtokens.js. */
export function tokenBlock(
  source: string,
  name: string,
): Record<string, string> {
  const open = source.indexOf(`${name}: {`);
  if (open < 0) throw new Error(`kmtokens.js has no ${name} block`);
  const body = source.slice(open, source.indexOf("}", open));
  const pairs = body.matchAll(/"(--[\w-]+)":\s*(["'])(.*?)\2/g);
  return Object.fromEntries([...pairs].map((m) => [m[1], m[3]]));
}

/** A missing key reads as undefined, which McpUiStyles allows for every key. */
function isStyles(
  variables: Record<string, string | undefined>,
): variables is McpUiStyles {
  return Object.keys(variables).every((key) => key.startsWith("--"));
}

/** Claude's documented style variables for a theme, read from design/mcp-app/kmtokens.js. */
export function claudeStyles(theme: Theme): McpUiStyles {
  const variables = {
    ...tokenBlock(kmtokens, theme),
    ...tokenBlock(kmtokens, "font"),
    ...tokenBlock(kmtokens, "radius"),
    ...tokenBlock(kmtokens, "border"),
  };
  if (!isStyles(variables))
    throw new Error("kmtokens.js holds a non-variable key");
  return variables;
}

export const WIDTHS = { wide: 760, narrow: 360 } as const;
export const FULLSCREEN = { width: 1100, height: 720 } as const;

export type View = {
  theme: Theme;
  width: number;
  displayMode: McpUiDisplayMode;
};

export function hostContext(view: View): McpUiHostContext {
  return {
    theme: view.theme,
    styles: { variables: claudeStyles(view.theme) },
    displayMode: view.displayMode,
    availableDisplayModes: ["inline", "fullscreen"],
    containerDimensions:
      view.displayMode === "fullscreen"
        ? FULLSCREEN
        : { width: view.width, maxHeight: 6000 },
    platform: "web",
    locale: "en-US",
  };
}

export type LogEntry = { kind: string; detail: unknown };

export type HarnessEvents = {
  log: (entry: LogEntry) => void;
  /** The app asked for a display mode; the harness answers with the one it applied. */
  displayMode: (mode: McpUiDisplayMode) => McpUiDisplayMode;
  height: (height: number) => void;
};

/** One AppBridge wired the way the harness hosts a card. Call connect(transport) next. */
export function harnessBridge(view: View, events: HarnessEvents): AppBridge {
  const bridge = new AppBridge(
    null,
    { name: "knowledge-mcp harness", version: "0.1.0" },
    {
      openLinks: {},
      logging: {},
      message: { text: {} },
      updateModelContext: { text: {} },
    },
    { hostContext: hostContext(view) },
  );
  bridge.oninitialized = () =>
    events.log({ kind: "initialized", detail: bridge.getAppCapabilities() });
  bridge.onmessage = (params) => {
    events.log({ kind: "ui/message", detail: params });
    return Promise.resolve({});
  };
  bridge.onupdatemodelcontext = (params) => {
    events.log({ kind: "ui/update-model-context", detail: params });
    return Promise.resolve({});
  };
  bridge.onrequestdisplaymode = (params) => {
    const mode = events.displayMode(params.mode);
    events.log({
      kind: "ui/request-display-mode",
      detail: { asked: params.mode, applied: mode },
    });
    return Promise.resolve({ mode });
  };
  bridge.onsizechange = (params) => {
    events.log({ kind: "size-changed", detail: params });
    if (typeof params.height === "number") events.height(params.height);
  };
  bridge.onloggingmessage = (params) =>
    events.log({ kind: "log", detail: params });
  return bridge;
}

export type Transport = Parameters<AppBridge["connect"]>[0];
