import { render, screen } from "@testing-library/react";

import { label } from "@/copy/en";

import { KeyValue, MAX_KEY_VALUE_ROWS } from "./key-value";

const row = (n: number) => ({ label: `L${n}`, value: `V${n}` });

describe("KeyValue", () => {
  it("shows each label beside its value", () => {
    render(<KeyValue rows={[{ label: label.changes, value: "3" }]} />);
    expect(screen.getByText("Changes").tagName).toBe("DT");
    expect(screen.getByText("3").tagName).toBe("DD");
  });

  it("allows five rows", () => {
    render(<KeyValue rows={[1, 2, 3, 4, 5].map(row)} />);
    expect(screen.getAllByRole("term")).toHaveLength(MAX_KEY_VALUE_ROWS);
  });

  it("refuses more than five rows", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(<KeyValue rows={[1, 2, 3, 4, 5, 6].map(row)} />),
    ).toThrow(/at most 5 rows/);
    spy.mockRestore();
  });
});
