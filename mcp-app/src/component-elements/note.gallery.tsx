import { line } from "@/copy/en";

import { Note } from "./note";

export default {
  id: "K06",
  name: "Note",
  stories: {
    Info: (
      <Note kind="info" fact="No naming rule for Design proposals">
        (dropped in conventions), so it goes beside cache-proposal.md.
      </Note>
    ),
    "Left out": (
      <Note kind="leftOut" fact={`${line.leftOut(2)}:`} onShowWhy={() => {}}>
        vendor-quote.xlsx, release-calendar.md.
      </Note>
    ),
    Warning: (
      <Note kind="warning">
        Prepared again because the file changed. C2’s current text is new.
      </Note>
    ),
  },
};
