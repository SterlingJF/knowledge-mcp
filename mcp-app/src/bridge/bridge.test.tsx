import { render, screen } from "@testing-library/react";
import type { App } from "@modelcontextprotocol/ext-apps/react";

import { CardView, registerCard } from "@/cards/registry";
import { cardHost } from "@/bridge/bridge";

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
