import { action } from "@/copy/en";

import { LinkButton } from "../link-button";

export default {
  id: "K15",
  name: "Link button",
  stories: {
    Closed: <LinkButton aria-expanded={false}>{action.showChange}</LinkButton>,
    Open: <LinkButton aria-expanded>{action.hideChange}</LinkButton>,
  },
};
