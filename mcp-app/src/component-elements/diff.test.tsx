import { render, screen } from "@testing-library/react";

import { Diff } from "./diff";

describe("Diff", () => {
  it("strikes removed lines and marks added ones", () => {
    render(
      <Diff
        lines={[
          { kind: "removed", text: "old" },
          { kind: "added", text: "new" },
        ]}
      />,
    );
    const removed = screen.getByText("old");
    expect(removed.tagName).toBe("DEL");
    expect(removed.className).toContain("line-through");
    expect(removed.className).toContain("--color-text-danger");
    const added = screen.getByText("new");
    expect(added.tagName).toBe("INS");
    expect(added.className).toContain("--color-text-success");
  });
});

test("long unbroken tokens wrap instead of running past the box", () => {
  const { container } = render(
    <Diff
      lines={[
        { kind: "removed", text: "a" },
        { kind: "added", text: "b" },
      ]}
    />,
  );
  for (const el of container.querySelectorAll("del, ins"))
    expect(el.className).toContain("[overflow-wrap:anywhere]");
});
