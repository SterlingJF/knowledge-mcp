import { Diff } from "./diff";

export default {
  id: "K09",
  name: "Diff",
  stories: {
    "Replaced line": (
      <Diff
        className="mt-0"
        lines={[
          { kind: "removed", text: "Title: Build schedule and cache rollout" },
          { kind: "added", text: "Title: Evening build retirement" },
        ]}
      />
    ),
  },
};
