import { render, screen } from "@testing-library/react";

import { PathChip, SourceChip } from "./chips";

test("line source reads file:line", () => {
  render(<SourceChip source={{ file: "meeting-notes.md", line_number: 15 }} />);
  expect(screen.getByText("meeting-notes.md:15")).toBeTruthy();
});

test("continuation drops the file", () => {
  render(
    <SourceChip continuation source={{ file: "meeting-notes.md", line_number: 19 }} />,
  );
  expect(screen.getByText(":19")).toBeTruthy();
});

test("place source reads file › place", () => {
  render(<SourceChip source={{ file: "deck.pptx", place: "slide 7" }} />);
  expect(screen.getByText("deck.pptx › slide 7")).toBeTruthy();
});

test("person source quotes the words", () => {
  render(<SourceChip speaker="you" source={{ said: "on its own" }} />);
  expect(screen.getByText("you: “on its own”")).toBeTruthy();
});

test("path chip shows the whole path", () => {
  const path = "~/Notes/Build Operations/a/very/long/path/cache-proposal.md";
  render(<PathChip path={path} />);
  expect(screen.getByText(path)).toBeTruthy();
});
