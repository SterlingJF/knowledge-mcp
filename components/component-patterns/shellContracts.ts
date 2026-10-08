import type { LucideIcon } from "lucide-react";
import type { RefObject } from "react";

export type SidebarMode = "closed" | "preview" | "docked";
export type SidebarSide = "left" | "right";

export const MAIN_CONTENT_SHAPES = [
  "document",
  "collection",
  "canvas",
  "stage",
] as const;
export const MAIN_CONTENT_SURFACES = ["paper", "bare"] as const;
export const MAIN_CONTENT_STAGE_BOUNDS = [
  "fully-bounded",
  "single-axis-bounded",
] as const;
export const MAIN_CONTENT_EXCESS_STRATEGIES = [
  "shrink",
  "condense",
  "summarise",
  "paginate",
] as const;

export type MainContentShape = (typeof MAIN_CONTENT_SHAPES)[number];
export type MainContentSurface = (typeof MAIN_CONTENT_SURFACES)[number];
export type MainContentStageBounds = (typeof MAIN_CONTENT_STAGE_BOUNDS)[number];
export type MainContentExcessStrategy =
  (typeof MAIN_CONTENT_EXCESS_STRATEGIES)[number];

export type ShellCommandAvailability = "available" | "unavailable";
export type ShellCommandOverflow = "protected" | "menu";
export type ShellCommandPresentation = "icon" | "compact-label" | "label";
export type ShellCommandRegion =
  "navigation" | "capability" | "view" | "main-context" | "trailing";

export type ShellCommand = {
  id: string;
  label: string;
  icon: LucideIcon;
  order: number;
  priority: number;
  overflow: ShellCommandOverflow;
  availability: ShellCommandAvailability;
  disabled: boolean;
  pressed: boolean;
  presentation: ShellCommandPresentation;
  widthUnits: number;
  fieldWidth?: number;
  command: () => void;
  focusRef?: RefObject<HTMLElement | null>;
  controls?: string;
  expanded?: boolean;
};
