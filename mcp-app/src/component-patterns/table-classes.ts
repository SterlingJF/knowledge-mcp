// Shared by P02 Change table and P08 Plan table: the row grid and the header label.
// Wide: the table's own columns. Narrow (container under 560px): each row stacks.
export const tableRow =
  "grid items-start gap-x-(--km-space-5) gap-y-(--km-space-3) border-b-(length:--border-width-regular) border-(--color-border-tertiary) py-(--km-space-4) @max-[560px]:grid-cols-1";

export const tableLabel =
  "text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-secondary)";
