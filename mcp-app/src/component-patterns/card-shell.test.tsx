import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { action, badge, frozen } from "@/copy/en";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";

const approve: CardAction = {
  label: "Save C1–C4",
  message: "Save C1–C4 to cache-proposal.md",
  frozenLine: frozen.approved,
  variant: "primary",
};
const notNow: CardAction = {
  label: action.notNow,
  message: "Not now",
  frozenLine: frozen.notSaved,
};

function shell(props: Partial<Parameters<typeof CardShell>[0]> = {}) {
  return render(
    <CardShell
      eyebrow="Evidence review"
      title="cache-proposal.md"
      meta="4 changes"
      badge={{ tone: "waiting", label: badge.waiting.needsOk }}
      why="Waits for you."
      actions={[approve, notNow]}
      {...props}
    >
      <p>Body text</p>
    </CardShell>,
  );
}

test("live: header, body, why line and the actions", () => {
  const onAction = vi.fn<(a: CardAction) => void>();
  shell({ onAction });
  expect(screen.getByText("cache-proposal.md")).toBeTruthy();
  expect(screen.getByText(badge.waiting.needsOk)).toBeTruthy();
  expect(screen.getByText("Waits for you.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Save C1–C4" }));
  expect(onAction).toHaveBeenCalledWith(approve);
});

test("refuses a third action", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  expect(() => shell({ actions: [approve, notNow, notNow] })).toThrow(
    /at most 2 actions/,
  );
});

test("frozen: actions gone, frozen line added, body unchanged", () => {
  shell({ state: "frozen", frozenLine: frozen.approved });
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByText(frozen.approved)).toBeTruthy();
  expect(screen.getByText("Body text")).toBeTruthy();
  expect(screen.getByText(badge.waiting.needsOk)).toBeTruthy();
  expect(screen.queryByText("Waits for you.")).toBeNull();
});

test("replaced: neutral Replaced badge and its frozen line", () => {
  shell({ state: "replaced" });
  expect(screen.queryByText(badge.waiting.needsOk)).toBeNull();
  expect(
    screen.getByText(badge.neutral.replaced).closest("[data-tone]"),
  ).toHaveProperty("dataset.tone", "neutral");
  expect(screen.getByText(frozen.replaced)).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});

test("Full view button only when asked for, and only while live", () => {
  const onFullView = vi.fn<() => void>();
  const { rerender } = render(
    <CardShell eyebrow="e" title="t" onFullView={onFullView} />,
  );
  fireEvent.click(screen.getByRole("button", { name: action.fullView }));
  expect(onFullView).toHaveBeenCalledOnce();
  rerender(
    <CardShell eyebrow="e" title="t" onFullView={onFullView} state="frozen" />,
  );
  expect(screen.queryByRole("button", { name: action.fullView })).toBeNull();
});

test("flat drops the frame", () => {
  const { container } = render(<CardShell eyebrow="e" title="t" flat />);
  const section = container.querySelector("section")!;
  expect(section.dataset.flat).toBe("true");
  expect(section.className).toMatch(/border-0/);
});
