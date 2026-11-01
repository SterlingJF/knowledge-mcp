import { clsx } from "clsx";
import type { ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

import { tokenClasses as t } from "@/generated/token-classes.auto";

// The token classes from kmtokens.js, so a token class replaces the core class it conflicts with.
const borderWidths = ["", "-x", "-y", "-t", "-r", "-b", "-l"] as const;
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      spacing: [...t.spacing],
      text: [...t.text],
      leading: [...t.leading],
      radius: [...t.radius],
      shadow: [...t.shadow],
      tracking: [...t.tracking],
      animate: [...t.animate],
      color: [...t.color],
    },
    classGroups: {
      opacity: [{ opacity: [...t.opacity] }],
      ...Object.fromEntries(
        borderWidths.map((side) => [
          `border-w${side}`,
          [{ [`border${side}`]: [...t.borderWidth] }],
        ]),
      ),
    },
  },
});

export function cn(...inputs: Array<ClassValue>): string {
  return twMerge(clsx(inputs));
}
