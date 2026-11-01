import { act, render } from "@testing-library/react";
import { vi } from "vitest";

import { CardHostProvider } from "@/bridge/bridge";

// A stand-in App: the provider wires its handlers onto it, and the test plays the host.
const app: Record<string, unknown> = {
  getHostContext: () => ({
    availableDisplayModes: ["inline"],
    safeAreaInsets: { top: 0, right: 0, bottom: 0, left: 0 },
  }),
};
vi.mock("@modelcontextprotocol/ext-apps/react", () => ({
  useApp: (options: { onAppCreated: (a: unknown) => void }) => {
    if (!app.created) {
      app.created = true;
      options.onAppCreated(app);
    }
    return { app };
  },
  useHostStyles: () => {},
}));

test("the root padding follows the host's safe area when it changes", () => {
  const { container } = render(<CardHostProvider>card</CardHostProvider>);
  const root = container.querySelector<HTMLElement>("[data-km-root]")!;
  const insets = () =>
    ["top", "right", "bottom", "left"].map((side) =>
      root.style.getPropertyValue(`--km-safe-${side}`),
    );
  expect(root.className).toContain("pt-(--km-safe-top)");
  expect(insets()).toEqual(["0px", "0px", "0px", "0px"]);
  act(() => {
    (app.onhostcontextchanged as (p: unknown) => void)({
      safeAreaInsets: { top: 44, right: 0, bottom: 34, left: 0 },
    });
  });
  expect(insets()).toEqual(["44px", "0px", "34px", "0px"]);
});
