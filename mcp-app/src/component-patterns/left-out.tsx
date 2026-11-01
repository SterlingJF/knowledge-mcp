// P03 Left out: files read but not cited, each with its reason from the data. Shown open: in the full
// view there is room, and a disclosure hiding two short lines costs a press for nothing.
import { PathChip } from "@/component-elements/chips";
import { Note } from "@/component-patterns/note";
import type { LeftOutFile } from "@/contracts/proposal";
import { line } from "@/copy/en";

export function LeftOut({
  files,
  className,
}: {
  files: LeftOutFile[];
  className?: string;
}) {
  return (
    <Note
      kind="leftOut"
      fact={line.leftOut(files.length)}
      className={className}
    >
      {files.length > 0 && (
        <dl className="flex flex-col gap-2">
          {files.map((f) => (
            <div key={f.file}>
              <dt>
                <PathChip path={f.file} />
              </dt>
              <dd>{f.reason}</dd>
            </div>
          ))}
        </dl>
      )}
    </Note>
  );
}
