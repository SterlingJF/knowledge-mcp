import { render, screen } from "@testing-library/react";

import { EvidenceMark } from "./evidence-mark";

test.each([
  ["supported", "Supported"],
  ["partly", "Partly answered"],
  ["conflicting", "Conflicting"],
  ["suggested", "Suggested"],
] as const)("%s reads %s with an icon", (mark, text) => {
  const { container } = render(<EvidenceMark mark={mark} />);
  expect(screen.getByText(text)).toBeTruthy();
  expect(container.querySelectorAll("svg")).toHaveLength(1);
});
