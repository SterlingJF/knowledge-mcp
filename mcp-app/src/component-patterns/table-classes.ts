// Shared by P02 Change table and P08 Plan table: the row grid and the header label.
// Wide: the table's own columns. Narrow (container under 560px): each row stacks.
export const tableRow =
  "grid items-start gap-x-km-gap-group gap-y-km-gap-row border-b-hairline border-border py-km-gap-row @max-[560px]:grid-cols-1";

export const tableLabel = "text-xs leading-xs font-semibold text-secondary";
