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
import { isYounger, useCardLifecycle } from "./card-lifecycle";
import { StubHost, stubHost } from "./host-double";

vi.mock("@/bridge/bridge", () => import("./host-double"));

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
      onAction={life.press}
      state={life.state}
      frozenLine={life.frozenLine}
    />
  );
}

test("a press freezes at once and sends the exact message, once", () => {
  const host = stubHost();
  render(
    <StubHost host={host}>
      <Card name="a" />
    </StubHost>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Save C1" }));
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(host.sent).toEqual(["Save C1 to a.md"]);
});

test("isYounger compares created_at, then seq", () => {
  const a = { subject: "a.md", created_at: "2026-10-28T10:00:00Z", seq: 1 };
  expect(isYounger({ ...a, created_at: "2026-10-28T10:00:01Z" }, a)).toBe(true);
  expect(isYounger({ ...a, seq: 2 }, a)).toBe(true);
  expect(isYounger(a, a)).toBe(false);
});

test("the older card about the same subject stands down", async () => {
  const at = "2026-10-28T10:00:00Z";
  const older = stubHost(
    {},
    { instance: { subject: "a.md", created_at: at, seq: 1 } },
  );
  const younger = stubHost(
    {},
    { instance: { subject: "a.md", created_at: at, seq: 2 } },
  );
  const other = stubHost(
    {},
    { instance: { subject: "b.md", created_at: at, seq: 0 } },
  );
  render(
    <>
      <StubHost host={older}>
        <Card name="older" />
      </StubHost>
      <StubHost host={other}>
        <Card name="other" />
      </StubHost>
    </>,
  );
  await act(async () => {
    render(
      <StubHost host={younger}>
        <Card name="younger" />
      </StubHost>,
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
  const younger = stubHost(
    {},
    { instance: { subject: "a.md", created_at: at, seq: 2 } },
  );
  const older = stubHost(
    {},
    { instance: { subject: "a.md", created_at: at, seq: 1 } },
  );
  render(
    <StubHost host={younger}>
      <Card name="younger" />
    </StubHost>,
  );
  await act(async () => {
    render(
      <StubHost host={older}>
        <Card name="older" />
      </StubHost>,
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
    <StubHost host={stubHost()}>
      <Card name="a" />
    </StubHost>,
  );
  expect(post).not.toHaveBeenCalled();
  post.mockRestore();
});
