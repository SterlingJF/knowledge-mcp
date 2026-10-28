// Dev-only host page: loads the built app (dist/index.html, the bytes served as
// ui://knowledge-mcp/app.html) into sandboxed iframes and talks to it over an AppBridge.

import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { PostMessageTransport } from "@modelcontextprotocol/ext-apps/app-bridge";
import type {
  AppBridge,
  McpUiDisplayMode,
} from "@modelcontextprotocol/ext-apps/app-bridge";

import {
  FULLSCREEN,
  WIDTHS,
  claudeStyles,
  harnessBridge,
  hostContext,
} from "./host";
import type { LogEntry, Theme, View } from "./host";
import first from "./proposal.result.json";
import younger from "./proposal.younger.result.json";

type Entry = LogEntry & { card: number; at: number };

async function loadApp(): Promise<string> {
  try {
    return (await import("../../dist/index.html?raw")).default;
  } catch {
    throw new Error(
      "No dist/index.html: run `pnpm --filter mcp-app build` first.",
    );
  }
}

function Frame({
  html,
  card,
  result,
  theme,
  width,
  onLog,
}: {
  html: string;
  card: number;
  result: Record<string, unknown>;
  theme: Theme;
  width: number;
  onLog: (entry: Entry) => void;
}) {
  const ref = useRef<HTMLIFrameElement>(null);
  const bridgeRef = useRef<AppBridge | null>(null);
  const [mode, setMode] = useState<McpUiDisplayMode>("inline");
  const [height, setHeight] = useState(120);
  const view: View = { theme, width, displayMode: mode };
  const viewRef = useRef(view);
  viewRef.current = view;

  useEffect(() => {
    const iframe = ref.current;
    if (!iframe?.contentWindow) return;
    const log = (entry: LogEntry) => onLog({ ...entry, card, at: Date.now() });
    const bridge = harnessBridge(viewRef.current, {
      log,
      displayMode: (asked) => {
        setMode(asked);
        return asked;
      },
      height: setHeight,
    });
    const initialized = bridge.oninitialized;
    bridge.oninitialized = (params) => {
      initialized?.(params);
      void bridge
        .sendToolInput({ arguments: {} })
        .then(() =>
          bridge.sendToolResult({
            content: [
              {
                type: "text",
                text: typeof result.card === "string" ? result.card : "",
              },
            ],
            structuredContent: result,
          }),
        )
        .then(() =>
          log({ kind: "host → tool result", detail: result.instance }),
        );
    };
    bridgeRef.current = bridge;
    void bridge.connect(
      new PostMessageTransport(iframe.contentWindow, iframe.contentWindow),
    );
    iframe.srcdoc = html;
    return () => void bridge.close();
  }, [html, card, result, onLog]);

  useEffect(() => {
    const context = hostContext(view);
    bridgeRef.current?.setHostContext(context);
    onLog({
      kind: "host → context",
      detail: { theme, width, displayMode: mode },
      card,
      at: Date.now(),
    });
  }, [theme, width, mode]);

  const full = mode === "fullscreen";
  return (
    <iframe
      ref={ref}
      title={`card ${card}`}
      sandbox="allow-scripts allow-same-origin"
      style={{
        display: "block",
        border: "none",
        background: "transparent",
        colorScheme: theme,
        width: full ? FULLSCREEN.width : width,
        height: full ? FULLSCREEN.height : height,
        outline: "1px dashed GrayText",
        marginBlock: 12,
      }}
    />
  );
}

function Harness() {
  const [html, setHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>("light");
  const [width, setWidth] = useState<number>(WIDTHS.wide);
  const [cards, setCards] = useState<Record<string, unknown>[]>([first]);
  const [log, setLog] = useState<Entry[]>([]);
  const onLog = useRef((entry: Entry) =>
    setLog((all) => [...all, entry]),
  ).current;

  useEffect(() => {
    loadApp().then(setHtml, (e: Error) => setError(e.message));
  }, []);

  const ground = claudeStyles(theme)["--color-background-tertiary"];
  const ink = claudeStyles(theme)["--color-text-primary"];
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "flex-start",
        gap: 16,
        padding: 16,
        minHeight: "100vh",
        boxSizing: "border-box",
        background: ground,
        color: ink,
        colorScheme: theme,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <main style={{ flex: "1 1 400px", minWidth: 0, overflowX: "auto" }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            Theme: {theme}
          </button>
          <button
            onClick={() =>
              setWidth(width === WIDTHS.wide ? WIDTHS.narrow : WIDTHS.wide)
            }
          >
            Width: {width}px
          </button>
          <button
            disabled={cards.length > 1}
            onClick={() => setCards([first, younger])}
          >
            Send a younger result for the same subject
          </button>
        </div>
        {error && <p role="alert">{error}</p>}
        {html &&
          cards.map((result, i) => (
            <Frame
              key={i}
              html={html}
              card={i + 1}
              result={result}
              theme={theme}
              width={width}
              onLog={onLog}
            />
          ))}
      </main>
      <aside
        aria-label="Host log"
        style={{
          flex: "1 1 320px",
          fontSize: 12,
          overflow: "auto",
          maxHeight: "95vh",
        }}
      >
        <h2 style={{ fontSize: 14 }}>Received and sent, in order</h2>
        <ol data-testid="log" style={{ paddingInlineStart: 20 }}>
          {log.map((entry, i) => (
            <li key={i}>
              <strong>
                card {entry.card} · {entry.kind}
              </strong>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                {JSON.stringify(entry.detail, null, 1)}
              </pre>
            </li>
          ))}
        </ol>
      </aside>
    </div>
  );
}

const root = document.getElementById("root");
if (!root) throw new Error("harness.html has no #root");
createRoot(root).render(
  <StrictMode>
    <Harness />
  </StrictMode>,
);
