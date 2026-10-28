import { render, screen } from "@testing-library/react";

import { PathChip, SourceChip } from "./chips";

// A chip's text is split into unbreakable words, so match the whole chip as the person reads it.
const chipText = (text: string) =>
  screen.getByText(
    (_, el) =>
      el?.textContent === text &&
      [...el.children].every((c) => c.textContent !== text),
  );

test("a file name never breaks at its hyphen", () => {
  render(
    <SourceChip source={{ file: "release-calendar.md", place: "row 2" }} />,
  );
  expect(chipText("release-calendar.md › row 2")).toBeTruthy();
  expect(screen.getByText("release-calendar.md").className).toContain(
    "whitespace-nowrap",
  );
});

test("line source reads file:line", () => {
  render(<SourceChip source={{ file: "meeting-notes.md", line_number: 15 }} />);
  expect(screen.getByText("meeting-notes.md:15")).toBeTruthy();
});

test("continuation drops the file", () => {
  render(
    <SourceChip
      continuation
      source={{ file: "meeting-notes.md", line_number: 19 }}
    />,
  );
  expect(screen.getByText(":19")).toBeTruthy();
});

test("place source reads file › place", () => {
  render(<SourceChip source={{ file: "deck.pptx", place: "slide 7" }} />);
  expect(chipText("deck.pptx › slide 7")).toBeTruthy();
});

test("person source quotes the words", () => {
  render(<SourceChip source={{ said: "on its own" }} />);
  expect(chipText("you: “on its own”")).toBeTruthy();
});

test("path chip shows the whole path", () => {
  const path = "~/Notes/Build Operations/a/very/long/path/cache-proposal.md";
  render(<PathChip path={path} />);
  expect(chipText(path)).toBeTruthy();
});
