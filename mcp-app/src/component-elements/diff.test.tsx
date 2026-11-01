import { render, screen } from "@testing-library/react";

import { Diff } from "./diff";

describe("Diff", () => {
  it("marks each line removed or added in its markup and with a sign, not by colour alone", () => {
    render(
      <Diff
        lines={[
          { kind: "removed", text: "old" },
          { kind: "added", text: "new" },
        ]}
      />,
    );
    const removed = screen.getByText("old").closest("del");
    expect(removed?.textContent).toBe("−old");
    const added = screen.getByText("new").closest("ins");
    expect(added?.textContent).toBe("+new");
  });
});
