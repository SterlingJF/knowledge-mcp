import { App } from "@modelcontextprotocol/ext-apps";

import { claudeStyles, harnessBridge, hostContext, tokenBlock } from "./host";
import type { LogEntry, Transport, View } from "./host";
import proposal from "./proposal.result.json";

type Message = Parameters<Transport["send"]>[0];

/** Two transports that hand each message to the other side, like postMessage between frames. */
function linkedPair(): [Transport, Transport] {
  const make = () => {
    const side: Transport & { peer?: Transport } = {
      start: () => Promise.resolve(),
      close: () => {
        side.onclose?.();
        return Promise.resolve();
      },
      send: (message: Message) => {
        queueMicrotask(() => side.peer?.onmessage?.(message));
        return Promise.resolve();
      },
    };
    return side;
  };
  const a = make();
  const b = make();
  a.peer = b;
  b.peer = a;
  return [a, b];
}

const VIEW: View = { theme: "light", width: 760, displayMode: "inline" };

async function hosted() {
  const log: Array<LogEntry> = [];
  const heights: Array<number> = [];
  let initialized = () => {};
  const ready = new Promise<void>((resolve) => (initialized = resolve));
  const bridge = harnessBridge(VIEW, {
    log: (entry) => {
      log.push(entry);
      if (entry.kind === "initialized") initialized();
    },
    displayMode: (mode) => mode,
    height: (h) => heights.push(h),
  });
  const app = new App(
    { name: "test app", version: "0" },
    {},
    { autoResize: false },
  );
  const [hostSide, appSide] = linkedPair();
  await bridge.connect(hostSide);
  await app.connect(appSide);
  await ready;
  return { app, bridge, log, heights };
}

describe("harness host", () => {
  it("reads kmtokens.js without running it", () => {
    expect(tokenBlock('radius: {\n "--r": "4px",\n}', "radius")).toEqual({
      "--r": "4px",
    });
  });

  it("sends Claude's light and dark style variables from kmtokens.js", () => {
    expect(claudeStyles("light")["--color-text-primary"]).toBe("#141413");
    expect(claudeStyles("dark")["--color-text-primary"]).toBe("#FAF9F5");
    expect(claudeStyles("dark")["--font-text-sm-size"]).toBe("14px");
  });

  it("offers inline and fullscreen and sizes the container per mode", () => {
    const inline = hostContext({ ...VIEW, width: 360 });
    expect(inline.availableDisplayModes).toEqual(["inline", "fullscreen"]);
    expect(inline.containerDimensions).toMatchObject({ width: 360 });
    const full = hostContext({ ...VIEW, displayMode: "fullscreen" });
    expect(full.containerDimensions).toMatchObject({ height: 720 });
  });

  it("gives the app the host context and the real proposal result", async () => {
    const { app, bridge } = await hosted();
    expect(app.getHostContext()?.theme).toBe("light");
    const got = new Promise((resolve) => {
      app.ontoolresult = (params) => resolve(params.structuredContent);
    });
    await bridge.sendToolInput({ arguments: {} });
    await bridge.sendToolResult({ content: [], structuredContent: proposal });
    expect(await got).toMatchObject({ schema: "knowledge-mcp/proposal/1" });
  });

  it("records messages, model context, display mode and size in order", async () => {
    const { app, log, heights } = await hosted();
    await app.updateModelContext({
      content: [{ type: "text", text: "digest" }],
    });
    await app.sendMessage({
      role: "user",
      content: [{ type: "text", text: "Approve C1" }],
    });
    const answer = await app.requestDisplayMode({ mode: "fullscreen" });
    await app.sendSizeChanged({ width: 760, height: 412 });
    await new Promise((r) => setTimeout(r, 0));
    expect(answer.mode).toBe("fullscreen");
    expect(heights).toEqual([412]);
    expect(log.map((e) => e.kind)).toEqual([
      "initialized",
      "ui/update-model-context",
      "ui/message",
      "ui/request-display-mode",
      "size-changed",
    ]);
  });
});
