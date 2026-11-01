import { act, fireEvent, render, screen } from "@testing-library/react";

import { Tabs } from "./tabs";

const tabs = [
  { value: "moves", label: "Moves", count: 3, content: <p>moves panel</p> },
  { value: "links", label: "Links", count: 5, content: <p>links panel</p> },
];

test("labels carry their count and the first tab is active", () => {
  render(<Tabs tabs={tabs} />);
  const first = screen.getByRole("tab", { name: "Moves (3)" });
  expect(first.getAttribute("aria-selected")).toBe("true");
  expect(screen.getByText("moves panel")).toBeTruthy();
  expect(screen.queryByText("links panel")).toBeNull();
});

test("clicking a tab shows its panel", () => {
  render(<Tabs tabs={tabs} />);
  fireEvent.click(screen.getByRole("tab", { name: "Links (5)" }));
  expect(screen.getByText("links panel")).toBeTruthy();
});

test("arrow keys move between tabs", async () => {
  render(<Tabs tabs={tabs} />);
  const first = screen.getByRole("tab", { name: "Moves (3)" });
  await act(async () => first.focus());
  await act(async () => {
    fireEvent.keyDown(first, { key: "ArrowRight", code: "ArrowRight" });
  });
  const second = screen.getByRole("tab", { name: "Links (5)" });
  expect(document.activeElement).toBe(second);
});
