import { CardSkeleton, SkeletonBlock } from "./skeleton";

// Gallery-only label: en.ts has no loading string yet (reported to the coordinator).
const loading = "Loading";

export default {
  id: "K10",
  name: "Skeleton",
  stories: {
    Blocks: (
      <div>
        <SkeletonBlock shape="title" />
        <SkeletonBlock />
        <SkeletonBlock shape="short" />
      </div>
    ),
    "Card (O01)": <CardSkeleton label={loading} rows={3} />,
    "Card with actions": <CardSkeleton label={loading} rows={2} actions={2} />,
  },
};
