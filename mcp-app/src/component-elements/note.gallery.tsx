import { action, line } from "@/copy/en";

import { LeftOutList, Note } from "./note";

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
      <Note kind="leftOut" fact={`${line.leftOut(2)}:`}>
        vendor-quote.xlsx, release-calendar.md. <u>{action.showWhy}</u>
      </Note>
    ),
    Warning: (
      <Note kind="warning">
        Prepared again because the file changed. C2’s current text is new.
      </Note>
    ),
    "Left-out list": (
      <Note kind="leftOut" fact={`${line.leftOut(2)}:`}>
        <LeftOutList
          files={[
            {
              file: "vendor-quote.xlsx",
              reason: "Pricing for another project.",
            },
            {
              file: "release-calendar.md",
              reason: "Dates only, nothing about caching.",
            },
          ]}
        />
      </Note>
    ),
  },
};
