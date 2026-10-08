// Shell sizes and timings the patterns compute with, read from the token map.

import { visualTokens } from "../generated/visual-tokens.auto";

const { components } = visualTokens;

/** A pixel or millisecond token, such as "220px", as a number. */
const amount = (token: string): number => Number.parseFloat(token);

export const shellMetrics = {
  appBarHeight: amount(components["app-bar"].height),
  mainContentMinWidth: amount(components["main-content"]["min-width"]),
  auxiliaryMinWidth: amount(components.auxiliary["width-min"]),
  auxiliaryDefaultWidth: amount(components.auxiliary["width-default"]),
} as const;

export const sidebarMetrics = {
  minWidth: amount(components.sidebar["width-min"]),
  defaultWidth: amount(components.sidebar["width-default"]),
  maxWidth: amount(components.sidebar["width-max"]),
} as const;

export const interactionMetrics = {
  sidebarPreviewCloseGrace: amount(components.sidebar["preview-close-grace"]),
} as const;
