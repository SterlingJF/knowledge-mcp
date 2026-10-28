import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { ChangeNumber, SelectAll } from "./change-number";

test("frozen shows only the number", () => {
  render(<ChangeNumber n={1} />);
  expect(screen.getByText("C1")).toBeTruthy();
  expect(screen.queryByRole("checkbox")).toBeNull();
});

test("clicking the row unticks a kept change", () => {
  const onKeptChange = vi.fn<(value: boolean) => void>();
  render(<ChangeNumber n={2} kept onKeptChange={onKeptChange} />);
  expect(screen.getByRole("checkbox").getAttribute("aria-checked")).toBe(
    "true",
  );
  fireEvent.click(screen.getByText("C2"));
  expect(onKeptChange).toHaveBeenCalledWith(false);
});

test("left out is unticked", () => {
  render(<ChangeNumber n={3} kept={false} onKeptChange={() => {}} />);
  expect(screen.getByRole("checkbox").getAttribute("aria-checked")).toBe(
    "false",
  );
});

test("All is mixed when some are left out, and selects every row", () => {
  const onChange = vi.fn<(value: boolean) => void>();
  render(<SelectAll keptCount={2} total={3} onChange={onChange} />);
  expect(screen.getByRole("checkbox").getAttribute("aria-checked")).toBe(
    "mixed",
  );
  fireEvent.click(screen.getByText("All"));
  expect(onChange).toHaveBeenCalledWith(true);
});

test("All clears every row when all are kept", () => {
  const onChange = vi.fn<(value: boolean) => void>();
  render(<SelectAll keptCount={3} total={3} onChange={onChange} />);
  expect(screen.getByRole("checkbox").getAttribute("aria-checked")).toBe(
    "true",
  );
  fireEvent.click(screen.getByText("All"));
  expect(onChange).toHaveBeenCalledWith(false);
});
