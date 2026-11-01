import { CardSkeleton } from "./skeleton";

export default {
  id: "K10",
  name: "Skeleton",
  stories: {
    "Card (O01)": <CardSkeleton rows={3} />,
    "Card with actions": <CardSkeleton rows={2} actions={2} />,
  },
};
