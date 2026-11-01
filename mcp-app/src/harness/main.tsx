// Dev-only host page: loads the built app (dist/index.html, the bytes served as
// ui://knowledge-mcp/app.html) into sandboxed iframes and talks to it over an AppBridge.

import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { PostMessageTransport } from "@modelcontextprotocol/ext-apps/app-bridge";
import type {
  AppBridge,
  McpUiDisplayMode,
} from "@modelcontextprotocol/ext-apps/app-bridge";

import { Button } from "@/component-core/button";
import "../styles.css";
import { FULLSCREEN, WIDTHS, harnessBridge, hostContext } from "./host";
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
  const viewRef = useRef<View>({ theme, width, displayMode: mode });

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
    const view: View = { theme, width, displayMode: mode };
    viewRef.current = view;
    const context = hostContext(view);
    bridgeRef.current?.setHostContext(context);
    onLog({
      kind: "host → context",
      detail: {
        theme,
        displayMode: mode,
        containerDimensions: context.containerDimensions,
      },
      card,
      at: Date.now(),
    });
  }, [theme, width, mode, card, onLog]);

  const full = mode === "fullscreen";
  return (
    <iframe
      ref={ref}
      title={`card ${card}`}
      sandbox="allow-scripts allow-same-origin"
      width={full ? FULLSCREEN.width : width}
      height={full ? FULLSCREEN.height : height}
      className="my-3 block border-0 bg-transparent outline-1 outline-muted-foreground outline-dashed"
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
  const onLog = useCallback(
    (entry: Entry) => setLog((all) => [...all, entry]),
    [],
  );

  useEffect(() => {
    loadApp().then(setHtml, (e: Error) => setError(e.message));
  }, []);

  return (
    <div
      data-theme={theme}
      data-harness
      className="flex min-h-screen w-max min-w-full flex-col gap-4 p-4"
    >
      <main className="w-max">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            Theme: {theme}
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              setWidth(width === WIDTHS.wide ? WIDTHS.narrow : WIDTHS.wide)
            }
          >
            Width: {width}px
          </Button>
          <Button
            variant="outline"
            disabled={cards.length > 1}
            onClick={() => setCards([first, younger])}
          >
            Send a younger result for the same subject
          </Button>
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
        className="max-h-screen max-w-190 overflow-auto text-xs"
      >
        <h2 className="text-sm">Received and sent, in order</h2>
        <ol data-testid="log" className="list-decimal ps-5">
          {log.map((entry, i) => (
            <li key={i}>
              <strong>
                card {entry.card} · {entry.kind}
              </strong>
              <pre className="m-0 whitespace-pre-wrap">
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
