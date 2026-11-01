import { render } from "@testing-library/react";

import { CurrentText } from "./text-lines";

describe("text lines", () => {
  it("reads a change's current text as its label, then the text", () => {
    const { container } = render(
      <CurrentText label="Title">Old title</CurrentText>,
    );
    expect(container.textContent).toBe("Title: Old title");
  });
});
