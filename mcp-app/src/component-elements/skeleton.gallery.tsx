import { CardSkeleton, SkeletonBlock } from "./skeleton";

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
    "Card (O01)": <CardSkeleton rows={3} />,
    "Card with actions": <CardSkeleton rows={2} actions={2} />,
  },
};
