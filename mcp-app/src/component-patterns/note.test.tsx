import { render, screen } from "@testing-library/react";

import { Note } from "./note";

test("reads the fact before the reason, as a note", () => {
  render(
    <Note kind="info" fact="No naming rule">
      so it goes beside.
    </Note>,
  );
  const note = screen.getByRole("note");
  expect(note.firstElementChild?.nextElementSibling?.textContent).toBe(
    "No naming rule",
  );
  expect(note.lastElementChild?.textContent).toBe("so it goes beside.");
});

test("a warning is announced", () => {
  render(<Note kind="warning">Prepared again.</Note>);
  expect(screen.getByRole("alert")).toBeTruthy();
});
