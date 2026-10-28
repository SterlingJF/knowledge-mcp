// P03 Left-out disclosure: files read but not cited, closed by default, each with its reason from the data when opened.
import { useState } from "react";

import { PathChip } from "@/component-elements/chips";
import { Note } from "@/component-elements/note";
import type { LeftOutFile } from "@/contracts/proposal";
import { line } from "@/copy/en";

export function LeftOut({
  files,
  defaultOpen = false,
  className,
}: {
  files: LeftOutFile[];
  defaultOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const count = line.leftOut(files.length);

  if (files.length === 0)
    return <Note kind="leftOut" fact={count} className={className} />;

  if (!open)
    return (
      <Note
        kind="leftOut"
        fact={`${count}:`}
        onShowWhy={() => setOpen(true)}
        className={className}
      >
        {`${files.map((f) => f.file).join(", ")}.`}
      </Note>
    );

  return (
    <Note kind="leftOut" fact={count} className={className}>
      <div className="mt-(--km-gap-row) grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-(--km-gap-group) gap-y-(--km-gap-row)">
        {files.map((f) => (
          <div key={f.file} className="contents">
            <PathChip path={f.file} />
            <span>{f.reason}</span>
          </div>
        ))}
      </div>
    </Note>
  );
}
