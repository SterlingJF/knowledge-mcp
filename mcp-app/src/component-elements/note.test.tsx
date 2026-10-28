import { render, screen } from "@testing-library/react";

import { LeftOutList, Note } from "./note";

test("bolds the fact before the reason", () => {
  render(<Note kind="info" fact="No naming rule">so it goes beside.</Note>);
  expect(screen.getByText("No naming rule").tagName).toBe("B");
  expect(screen.getByRole("note").textContent).toBe("No naming rule so it goes beside.");
});

test("a warning is announced", () => {
  render(<Note kind="warning">Prepared again.</Note>);
  expect(screen.getByRole("alert")).toBeTruthy();
});

test("left-out list pairs each file with its reason", () => {
  render(
    <LeftOutList
      files={[
        { file: "vendor-quote.xlsx", reason: "Pricing, not caching." },
        { file: "release-calendar.md", reason: "Dates only." },
      ]}
    />,
  );
  const items = screen.getAllByRole("listitem");
  expect(items).toHaveLength(2);
  expect(items[0].textContent).toBe("vendor-quote.xlsxPricing, not caching.");
});
