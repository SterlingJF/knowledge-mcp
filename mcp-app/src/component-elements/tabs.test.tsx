import { render, screen } from "@testing-library/react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

test("the parts compose into tabs with the line look", () => {
  render(
    <Tabs defaultValue="a">
      <TabsList>
        <TabsTrigger value="a">A</TabsTrigger>
        <TabsTrigger value="b">B</TabsTrigger>
      </TabsList>
      <TabsContent value="a">panel a</TabsContent>
      <TabsContent value="b">panel b</TabsContent>
    </Tabs>,
  );
  const first = screen.getByRole("tab", { name: "A" });
  expect(first.getAttribute("aria-selected")).toBe("true");
  expect(first.className).toContain("after:h-(--km-underline)");
  expect(screen.getByRole("tablist").getAttribute("data-variant")).toBe("line");
  expect(screen.getByText("panel a")).toBeTruthy();
});
