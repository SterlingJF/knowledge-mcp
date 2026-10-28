import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { vi } from "vitest";

import { frozen } from "@/copy/en";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";
import { isYounger, lifecycleProps, useCardLifecycle } from "./card-lifecycle";
import type { CardLifecycle } from "./card-lifecycle";
import { StaticCardHost, stubCardHost } from "@/bridge/static";

const save: CardAction = {
  label: "Save C1",
  message: "Save C1 to a.md",
  frozenLine: frozen.approved,
};

function Card({ name }: { name: string }) {
  const life = useCardLifecycle();
  return (
    <CardShell
      eyebrow={name}
      title={name}
      actions={[save]}
      {...lifecycleProps(life)}
    />
  );
}

test("a press freezes at once and sends the exact message, once", () => {
  const host = stubCardHost();
  render(
    <StaticCardHost host={host}>
      <Card name="a" />
    </StaticCardHost>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Save C1" }));
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(host.sent).toEqual(["Save C1 to a.md"]);
});

test("isYounger compares created_at as strings, then seq when equal or missing", () => {
  const a = { subject: "a.md", created_at: "2026-10-28T10:00:00Z", seq: 1 };
  expect(
    isYounger({ ...a, created_at: "2026-10-28T10:00:01Z", seq: 0 }, a),
  ).toBe(true);
  expect(isYounger({ ...a, seq: 2 }, a)).toBe(true);
  expect(isYounger({ subject: "a.md", seq: 2 }, a)).toBe(true);
  expect(isYounger(a, a)).toBe(false);
});

test("the older card about the same subject stands down", async () => {
  const at = "2026-10-28T10:00:00Z";
  const older = stubCardHost({
    result: { instance: { subject: "a.md", created_at: at, seq: 1 } },
  });
  const younger = stubCardHost({
    result: { instance: { subject: "a.md", created_at: at, seq: 2 } },
  });
  const other = stubCardHost({
    result: { instance: { subject: "b.md", created_at: at, seq: 0 } },
  });
  render(
    <>
      <StaticCardHost host={older}>
        <Card name="older" />
      </StaticCardHost>
      <StaticCardHost host={other}>
        <Card name="other" />
      </StaticCardHost>
    </>,
  );
  await act(async () => {
    render(
      <StaticCardHost host={younger}>
        <Card name="younger" />
      </StaticCardHost>,
    );
  });
  await waitFor(() =>
    expect(
      document.querySelectorAll('section[data-state="replaced"]'),
    ).toHaveLength(1),
  );
  const replaced = document.querySelector('section[data-state="replaced"]')!;
  expect(replaced.textContent).toContain("older");
  expect(replaced.textContent).toContain(frozen.replaced);
});

test("an older card mounting late learns it is already replaced", async () => {
  const at = "2026-10-28T10:00:00Z";
  const younger = stubCardHost({
    result: { instance: { subject: "a.md", created_at: at, seq: 2 } },
  });
  const older = stubCardHost({
    result: { instance: { subject: "a.md", created_at: at, seq: 1 } },
  });
  render(
    <StaticCardHost host={younger}>
      <Card name="younger" />
    </StaticCardHost>,
  );
  await act(async () => {
    render(
      <StaticCardHost host={older}>
        <Card name="older" />
      </StaticCardHost>,
    );
  });
  await waitFor(() =>
    expect(
      document.querySelector('section[data-state="replaced"]')?.textContent,
    ).toContain("older"),
  );
});

test("without an instance key nothing is announced", () => {
  const post = vi.spyOn(BroadcastChannel.prototype, "postMessage");
  render(
    <StaticCardHost host={stubCardHost()}>
      <Card name="a" />
    </StaticCardHost>,
  );
  expect(post).not.toHaveBeenCalled();
  post.mockRestore();
});

const at = "2026-10-28T10:00:00Z";
const key = (seq: number) => ({
  result: { instance: { subject: "a.md", created_at: at, seq } },
});

test("a pressed card keeps its frozen line when a younger card arrives", async () => {
  const older = stubCardHost(key(1));
  render(
    <StaticCardHost host={older}>
      <Card name="older" />
    </StaticCardHost>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Save C1" }));
  await act(async () => {
    render(
      <StaticCardHost host={stubCardHost(key(2))}>
        <Card name="younger" />
      </StaticCardHost>,
    );
  });
  await new Promise((resolve) => setTimeout(resolve, 20));
  expect(document.querySelector('section[data-state="replaced"]')).toBeNull();
  expect(screen.getByText(frozen.approved)).toBeTruthy();
});

test("a replaced card ignores a press", async () => {
  const older = stubCardHost(key(1));
  let life: CardLifecycle | undefined;
  function Probe() {
    life = useCardLifecycle();
    return null;
  }
  render(
    <StaticCardHost host={older}>
      <Probe />
    </StaticCardHost>,
  );
  await act(async () => {
    render(
      <StaticCardHost host={stubCardHost(key(2))}>
        <Card name="younger" />
      </StaticCardHost>,
    );
  });
  await waitFor(() => expect(life?.state).toBe("replaced"));
  act(() => life?.press(save));
  expect(older.sent).toEqual([]);
  expect(life?.state).toBe("replaced");
});

test("the channel is closed on unmount", () => {
  const close = vi.spyOn(BroadcastChannel.prototype, "close");
  const { unmount } = render(
    <StaticCardHost host={stubCardHost(key(1))}>
      <Card name="a" />
    </StaticCardHost>,
  );
  expect(close).not.toHaveBeenCalled();
  unmount();
  expect(close).toHaveBeenCalledOnce();
  close.mockRestore();
});
