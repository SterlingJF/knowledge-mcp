import { LeftOut } from "../left-out";

const files = [
  {
    file: "vendor-quote.xlsx",
    reason:
      "Prices a hosted build service. This proposal decides on retiring a build, so it answers none of its questions.",
  },
  {
    file: "release-calendar.md",
    reason: "Covers release dates, which this proposal doesn’t.",
  },
];

export default {
  id: "P03",
  name: "Left-out disclosure",
  stories: {
    Closed: <LeftOut files={files} />,
    Open: <LeftOut files={files} defaultOpen />,
    "None left out": <LeftOut files={[]} />,
  },
};
