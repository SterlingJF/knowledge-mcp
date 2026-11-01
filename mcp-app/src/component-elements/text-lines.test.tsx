import { render, screen } from "@testing-library/react";

import { CurrentText, Eyebrow, Title } from "./text-lines";

describe("text lines", () => {
  it("renders eyebrow uppercase in tertiary", () => {
    render(<Eyebrow>Proposed changes</Eyebrow>);
    const el = screen.getByText("Proposed changes");
    expect(el.className).toContain("uppercase");
    expect(el.className).toContain("text-muted-foreground");
  });

  it("renders title semibold at heading size", () => {
    render(<Title>A title</Title>);
    expect(screen.getByText("A title").className).toContain("text-base");
  });

  it("shows current text as bold label then tertiary text", () => {
    render(<CurrentText label="Title">Old title</CurrentText>);
    expect(screen.getByText("Title:").className).toContain("font-semibold");
    expect(screen.getByText("Old title").className).toContain(
      "text-muted-foreground",
    );
  });
});
