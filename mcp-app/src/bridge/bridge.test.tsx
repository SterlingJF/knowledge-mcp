import { render, screen } from "@testing-library/react";
import type { App } from "@modelcontextprotocol/ext-apps/react";

import { CardView, registerCard } from "@/cards/registry";
import { change } from "@/copy/en";
import { cardHost, useCardHost } from "@/bridge/bridge";
import { StaticCardHost, stubCardHost } from "@/bridge/static";

// A stand-in for the connected App: records what the card asked the host to do.
function stubApp(modes: Array<string>) {
  const sent: Array<unknown> = [];
  const requested: Array<unknown> = [];
  const app = {
    getHostContext: () => ({ availableDisplayModes: modes }),
    sendMessage: async (params: unknown) => {
      sent.push(params);
      return {};
    },
    requestDisplayMode: async (params: unknown) => {
      requested.push(params);
      return { mode: "fullscreen" };
    },
  } as unknown as App;
  return { app, sent, requested };
}

describe("cardHost", () => {
  it("sends a button's words as the person's message", async () => {
    const { app, sent } = stubApp(["inline"]);
    await cardHost(app, null, "inline").send("Save C1–C4 to cache-proposal.md");
    expect(sent).toEqual([
      {
        role: "user",
        content: [{ type: "text", text: "Save C1–C4 to cache-proposal.md" }],
      },
    ]);
  });

  it("sends model context before the message when a card passes one", async () => {
    const calls: Array<string> = [];
    const app = {
      getHostContext: () => ({ availableDisplayModes: ["inline"] }),
      updateModelContext: async () => {
        calls.push("context");
        return {};
      },
      sendMessage: async () => {
        calls.push("message");
        return {};
      },
    } as unknown as App;
    await cardHost(app, null, "inline").send(
      "Save C1–C4 to cache-proposal.md",
      {
        based_on: { document_digest: "sha256:" + "a".repeat(64) },
      },
    );
    expect(calls).toEqual(["context", "message"]);
  });

  it("opens the full view only when the host offers fullscreen", async () => {
    const without = stubApp(["inline"]);
    const host = cardHost(without.app, null, "inline");
    await host.requestFullView();
    expect(host.canFullView).toBe(false);
    expect(without.requested).toEqual([]);

    const offered = stubApp(["inline", "fullscreen"]);
    const full = cardHost(offered.app, null, "inline");
    await full.requestFullView();
    expect(full.canFullView).toBe(true);
    expect(offered.requested).toEqual([{ mode: "fullscreen" }]);
  });
});

describe("CardView", () => {
  it("draws the card registered for the result's schema", () => {
    registerCard("knowledge-mcp/test/1", () => <p>test card</p>);
    render(<CardView result={{ schema: "knowledge-mcp/test/1" }} />);
    expect(screen.getByText("test card").textContent).toBe("test card");
  });

  it("draws nothing for a schema without a card, leaving the text card", () => {
    const { container } = render(
      <CardView result={{ schema: "knowledge-mcp/other/1" }} />,
    );
    expect(container.innerHTML).toBe("");
  });
});

describe("StaticCardHost", () => {
  it("lets a card send through a recorded stand-in host", async () => {
    const host = stubCardHost();
    function Sender() {
      const { send } = useCardHost();
      return <button onClick={() => void send("Not now")}>Not now</button>;
    }
    render(
      <StaticCardHost host={host}>
        <Sender />
      </StaticCardHost>,
    );
    screen.getByText("Not now").click();
    await Promise.resolve();
    expect(host.sent).toEqual(["Not now"]);
  });
});

describe("change.list", () => {
  it("writes change numbers as runs", () => {
    expect(change.list([4, 1, 2, 3])).toBe("C1–C4");
    expect(change.list([1, 3, 4])).toBe("C1, C3–C4");
    expect(change.list([2])).toBe("C2");
  });
});
