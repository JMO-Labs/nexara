/**
 * @file tests/unit/ui/Tabs.test.tsx
 * @brief Value-based tabs keyboard + panel behavior.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Tabs, TabList, Tab, TabPanel } from "@/components/ui/Tabs";

function setup() {
  return render(
    <Tabs defaultValue="a">
      <TabList>
        <Tab value="a">Alpha</Tab>
        <Tab value="b">Beta</Tab>
      </TabList>
      <TabPanel value="a">Panel A</TabPanel>
      <TabPanel value="b">Panel B</TabPanel>
    </Tabs>,
  );
}

describe("Tabs", () => {
  it("arrow-right moves focus to next tab", async () => {
    const user = userEvent.setup();
    setup();
    await user.tab();
    expect(screen.getByRole("tab", { name: "Alpha" })).toHaveFocus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Beta" })).toHaveFocus();
  });

  it("selecting a tab shows its panel", async () => {
    const user = userEvent.setup();
    setup();
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Panel A");
    await user.click(screen.getByRole("tab", { name: "Beta" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Panel B");
  });
});
