import { render, screen } from "@testing-library/react";

import { CurrentText, Eyebrow, Title } from "./text-lines";

describe("text lines", () => {
  it("renders eyebrow uppercase in tertiary", () => {
    render(<Eyebrow>Proposed changes</Eyebrow>);
    const el = screen.getByText("Proposed changes");
    expect(el.className).toContain("uppercase");
    expect(el.className).toContain("--color-text-tertiary");
  });

  it("renders title semibold at heading size", () => {
    render(<Title>A title</Title>);
    expect(screen.getByText("A title").className).toContain(
      "--font-heading-md-size",
    );
  });

  it("shows current text as bold label then tertiary text", () => {
    render(<CurrentText label="Title">Old title</CurrentText>);
    expect(screen.getByText("Title:").className).toContain(
      "--font-weight-semibold",
    );
    expect(screen.getByText("Old title").className).toContain(
      "--color-text-tertiary",
    );
  });
});
