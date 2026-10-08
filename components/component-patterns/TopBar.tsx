"use client";

// File: components/component-patterns/TopBar.tsx

import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "../component-core/dropdown-menu";
import { Button } from "../component-elements/button";
import { MoreHorizontal, PanelLeft, PanelRight } from "lucide-react";
import { useLayoutEffect, useRef } from "react";

import { IconActionButton } from "./IconActionButton";

import type {
  ShellCommand,
  ShellCommandAvailability,
  ShellCommandRegion,
  SidebarMode,
  SidebarSide,
} from "./shellContracts";
import type { CSSProperties, ReactNode, RefObject } from "react";

export const SHELL_COMMAND_WIDTH_UNIT = 29;
const SHELL_COMMAND_GAP = 4;

export type ShellPrimaryContribution = {
  id: string;
  order: number;
  availability: ShellCommandAvailability;
  placement: "window-center" | "main-start";
  divider: "none" | "main-region";
  content: ReactNode;
};

/** Renders beside the primary. The shell never reads the content. */
export type ShellTabsContribution = {
  content: ReactNode;
};

export type TopBarSidebarControl = {
  side: SidebarSide;
  mode: SidebarMode;
  controls: string;
  triggerRef: RefObject<HTMLButtonElement | null>;
  onPointerEnter: () => void;
  onPointerLeave: () => void;
  onClick: () => void;
};

type CommandsByRegion = Record<ShellCommandRegion, Array<ShellCommand>>;

export type ShellContributionInput = {
  primaryContributions: Array<ShellPrimaryContribution>;
  navigationCommands: Array<ShellCommand>;
  capabilityCommands: Array<ShellCommand>;
  viewCommands: Array<ShellCommand>;
  mainContextCommands: Array<ShellCommand>;
  trailingCommands: Array<ShellCommand>;
  /** Full capability set used for leading-boundary width. Defaults to `capabilityCommands`. */
  reservedCapabilityCommands?: Array<ShellCommand>;
  availableCommandWidthUnits: number;
  tabs?: ShellTabsContribution;
};

export type ResolvedShellContributions = {
  primaryContributions: Array<ShellPrimaryContribution>;
  activePrimaryId: string | null;
  tabs?: ShellTabsContribution;
  visible: CommandsByRegion;
  overflow: Array<ShellCommand>;
  usedCommandWidthUnits: number;
  commandRailWidth: number;
  /** Leading navigation width after the endpoint trigger, including its gap. */
  leadingChromeOffset: number;
  /** Content-start offset after capabilities. */
  leadingContributionsOffset: number;
  protectedOverCapacity: boolean;
};

const regionOrder: Array<ShellCommandRegion> = [
  "navigation",
  "capability",
  "view",
  "main-context",
  "trailing",
];

const byOrderAndId = (left: ShellCommand, right: ShellCommand) =>
  left.order - right.order || left.id.localeCompare(right.id);

const commandFieldWidth = (item: ShellCommand) =>
  item.fieldWidth ??
  (item.presentation === "icon"
    ? 27
    : item.presentation === "label"
      ? 90
      : item.widthUnits * SHELL_COMMAND_WIDTH_UNIT);

export function resolveShellContributions({
  primaryContributions,
  navigationCommands,
  capabilityCommands,
  viewCommands,
  mainContextCommands,
  trailingCommands,
  reservedCapabilityCommands,
  availableCommandWidthUnits,
  tabs,
}: ShellContributionInput): ResolvedShellContributions {
  const sortedPrimaries = [...primaryContributions].sort(
    (left, right) =>
      left.order - right.order || left.id.localeCompare(right.id),
  );
  const primaryIds = new Set<string>();
  for (const item of sortedPrimaries) {
    if (!item.id.trim())
      throw new Error("Shell primary IDs must not be empty.");
    if (primaryIds.has(item.id)) {
      throw new Error(`Duplicate shell primary ID: ${item.id}`);
    }
    primaryIds.add(item.id);
  }
  const activePrimaries = sortedPrimaries.filter(
    (item) => item.availability === "available",
  );
  if (sortedPrimaries.length > 0 && activePrimaries.length !== 1) {
    throw new Error(
      "Shell requires exactly one available primary contribution.",
    );
  }

  const commands: CommandsByRegion = {
    navigation: navigationCommands,
    capability: capabilityCommands,
    view: viewCommands,
    "main-context": mainContextCommands,
    trailing: trailingCommands,
  };
  const ids = new Set<string>();
  for (const region of regionOrder) {
    for (const item of commands[region]) {
      if (!item.id.trim())
        throw new Error("Shell command IDs must not be empty.");
      if (item.presentation === "icon" && !item.label.trim()) {
        throw new Error("Icon shell command labels must not be empty.");
      }
      if (ids.has(item.id))
        throw new Error(`Duplicate shell command ID: ${item.id}`);
      if (!Number.isInteger(item.widthUnits) || item.widthUnits < 1) {
        throw new Error(`Invalid shell command width units: ${item.id}`);
      }
      ids.add(item.id);
    }
  }

  const available = regionOrder.flatMap((region) =>
    commands[region]
      .filter((item) => item.availability === "available")
      .sort(byOrderAndId)
      .map((item) => ({ item, region })),
  );
  const protectedItems = available.filter(
    ({ item }) => item.overflow === "protected",
  );
  const menuCandidates = available
    .filter(({ item }) => item.overflow === "menu")
    .sort(
      (left, right) =>
        right.item.priority - left.item.priority ||
        regionOrder.indexOf(left.region) - regionOrder.indexOf(right.region) ||
        byOrderAndId(left.item, right.item),
    );
  const capacity = Math.max(0, Math.floor(availableCommandWidthUnits));
  const protectedWidth = protectedItems.reduce(
    (total, { item }) => total + item.widthUnits,
    0,
  );
  const allMenuWidth = menuCandidates.reduce(
    (total, { item }) => total + item.widthUnits,
    0,
  );
  const menuFits = protectedWidth + allMenuWidth <= capacity;
  let menuBudget = Math.max(0, capacity - protectedWidth - (menuFits ? 0 : 1));
  const visibleMenuIds = new Set<string>();
  for (const { item } of menuCandidates) {
    if (item.widthUnits > menuBudget) continue;
    visibleMenuIds.add(item.id);
    menuBudget -= item.widthUnits;
  }
  const visibleIds = new Set([
    ...protectedItems.map(({ item }) => item.id),
    ...visibleMenuIds,
  ]);
  const visible = Object.fromEntries(
    regionOrder.map((region) => [
      region,
      available
        .filter(
          (entry) => entry.region === region && visibleIds.has(entry.item.id),
        )
        .map(({ item }) => item),
    ]),
  ) as CommandsByRegion;
  const overflow = menuCandidates
    .filter(({ item }) => !visibleMenuIds.has(item.id))
    .map(({ item }) => item);
  const visibleWidth = available
    .filter(({ item }) => visibleIds.has(item.id))
    .reduce((total, { item }) => total + item.widthUnits, 0);
  const commandRailItems = (
    ["view", "main-context", "trailing"] as const
  ).flatMap((region) => visible[region]);
  const renderedRailItems = [
    ...commandRailItems,
    ...(overflow.length > 0 ? [null] : []),
  ];
  const commandRailWidth =
    renderedRailItems.reduce(
      (total, item) => total + (item ? commandFieldWidth(item) : 27),
      0,
    ) +
    Math.max(0, renderedRailItems.length - 1) * SHELL_COMMAND_GAP;

  // Pane clearance uses navigation field geometry (AppShell.tsx).
  const navigationWidth =
    visible.navigation.reduce(
      (total, item) => total + commandFieldWidth(item),
      0,
    ) +
    Math.max(0, visible.navigation.length - 1) * SHELL_COMMAND_GAP;
  const leadingChromeOffset =
    visible.navigation.length > 0 ? navigationWidth + SHELL_COMMAND_GAP : 0;

  // Reserved capability widths set content start. Content inset supplies trailing separation.
  const reserved = reservedCapabilityCommands ?? capabilityCommands;
  const leadingContributionsOffset =
    reserved.reduce((total, item) => total + commandFieldWidth(item), 0) +
    Math.max(0, reserved.length - 1) * SHELL_COMMAND_GAP;

  return {
    primaryContributions: sortedPrimaries,
    activePrimaryId: activePrimaries[0]?.id ?? null,
    tabs,
    visible,
    overflow,
    usedCommandWidthUnits: visibleWidth + (overflow.length > 0 ? 1 : 0),
    commandRailWidth,
    leadingChromeOffset,
    leadingContributionsOffset,
    protectedOverCapacity:
      protectedWidth + (overflow.length > 0 ? 1 : 0) > capacity,
  };
}

export type TopBarProps = ResolvedShellContributions & {
  direction: "ltr" | "rtl";
  /** Absent when the surface suppresses that pane's trigger. */
  leftSidebarControl?: TopBarSidebarControl;
  rightSidebarControl?: TopBarSidebarControl;
  onCommandElementChange?: (id: string, element: HTMLElement | null) => void;
};

const renderPrimary = (
  item: ShellPrimaryContribution,
  activePrimaryId: string | null,
  direction: "ltr" | "rtl",
) => {
  const active = item.id === activePrimaryId;
  return (
    <div
      key={item.id}
      className={`app-top-bar-primary app-top-bar-primary-${item.placement}`}
      dir={direction}
      data-primary-contribution={item.id}
      data-active={active}
      aria-hidden={!active}
      inert={!active ? true : undefined}
    >
      {item.content}
    </div>
  );
};

export function TopBar({
  direction,
  primaryContributions,
  activePrimaryId,
  tabs,
  visible,
  overflow,
  leadingChromeOffset,
  leadingContributionsOffset,
  leftSidebarControl,
  rightSidebarControl,
  onCommandElementChange,
}: TopBarProps) {
  const activePrimary = primaryContributions.find(
    (item) => item.id === activePrimaryId,
  );
  const moreTriggerRef = useRef<HTMLButtonElement>(null);
  const focusedCommandIdRef = useRef<string | null>(null);
  const pendingOverflowFocusIdRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    const focusedId = focusedCommandIdRef.current;
    if (!focusedId || !overflow.some((item) => item.id === focusedId)) return;
    pendingOverflowFocusIdRef.current = focusedId;
    moreTriggerRef.current?.focus();
    focusedCommandIdRef.current = null;
  }, [overflow]);

  return (
    <header
      className="app-top-bar"
      data-primary-presentation={
        activePrimary
          ? activePrimary.placement === "window-center"
            ? "centered"
            : "content"
          : undefined
      }
      data-divider={activePrimary?.divider ?? "none"}
      style={
        {
          "--app-bar-leading-chrome-offset": `${leadingChromeOffset}px`,
          "--app-bar-leading-contributions-offset": `${leadingContributionsOffset}px`,
        } as CSSProperties
      }
    >
      {leftSidebarControl ? (
        <div className="app-top-bar-endpoint app-top-bar-endpoint-left">
          <SidebarTrigger {...leftSidebarControl} />
        </div>
      ) : null}

      {/* Navigation stays chrome. Capabilities transfer into an open pane. */}
      <div className="app-top-bar-chrome" dir={direction}>
        <CommandRegion
          region="navigation"
          commands={visible.navigation}
          focusedCommandIdRef={focusedCommandIdRef}
          onCommandElementChange={onCommandElementChange}
        />
      </div>

      <div className="app-top-bar-left-contributions" dir={direction}>
        <CommandRegion
          region="capability"
          commands={visible.capability}
          capabilityPresentation="compact"
          focusedCommandIdRef={focusedCommandIdRef}
          onCommandElementChange={onCommandElementChange}
        />
      </div>

      {/* Main-span axis is physical LTR. Children restore content direction. */}
      <div className="app-top-bar-main-span" dir="ltr">
        {primaryContributions
          .filter((item) => item.placement === "main-start")
          .map((item) => renderPrimary(item, activePrimaryId, direction))}
        {tabs ? (
          <div
            className="app-top-bar-tabs"
            data-top-bar-region="tabs"
            dir={direction}
          >
            {tabs.content}
          </div>
        ) : null}
      </div>

      {primaryContributions
        .filter((item) => item.placement !== "main-start")
        .map((item) => renderPrimary(item, activePrimaryId, direction))}

      <div className="app-top-bar-command-rail" dir={direction}>
        <CommandRegion
          region="view"
          commands={visible.view}
          focusedCommandIdRef={focusedCommandIdRef}
          onCommandElementChange={onCommandElementChange}
        />
        <CommandRegion
          region="main-context"
          commands={visible["main-context"]}
          focusedCommandIdRef={focusedCommandIdRef}
          onCommandElementChange={onCommandElementChange}
        />
        <CommandRegion
          region="trailing"
          commands={visible.trailing}
          focusedCommandIdRef={focusedCommandIdRef}
          onCommandElementChange={onCommandElementChange}
        />
        {overflow.length > 0 ? (
          <OverflowMenu
            commands={overflow}
            triggerRef={moreTriggerRef}
            focusedCommandIdRef={focusedCommandIdRef}
            pendingOverflowFocusIdRef={pendingOverflowFocusIdRef}
            onCommandElementChange={onCommandElementChange}
          />
        ) : null}
      </div>

      {rightSidebarControl ? (
        <div className="app-top-bar-endpoint app-top-bar-endpoint-right">
          <SidebarTrigger {...rightSidebarControl} />
        </div>
      ) : null}
    </header>
  );
}

function SidebarTrigger({
  side,
  mode,
  controls,
  triggerRef,
  onPointerEnter,
  onPointerLeave,
  onClick,
}: TopBarSidebarControl) {
  const verb =
    mode === "closed" ? "Open" : mode === "preview" ? "Dock" : "Close";
  const label = `${verb} ${side} sidebar`;
  const Icon = side === "left" ? PanelLeft : PanelRight;

  return (
    <Button
      ref={triggerRef}
      type="button"
      variant="ghost"
      size="icon-sm"
      data-sidebar-trigger={side}
      aria-label={label}
      aria-controls={controls}
      aria-expanded={mode !== "closed"}
      onPointerEnter={onPointerEnter}
      onPointerLeave={onPointerLeave}
      onClick={onClick}
    >
      <Icon aria-hidden="true" />
    </Button>
  );
}

function CommandRegion({
  region,
  commands,
  capabilityPresentation,
  focusedCommandIdRef,
  onCommandElementChange,
}: {
  region: ShellCommandRegion;
  commands: Array<ShellCommand>;
  capabilityPresentation?: "compact";
  focusedCommandIdRef: RefObject<string | null>;
  onCommandElementChange?: TopBarProps["onCommandElementChange"];
}) {
  if (commands.length === 0) return null;

  return (
    <div
      className="app-top-bar-command-region"
      data-command-region={region}
      data-capability-presentation={capabilityPresentation}
    >
      {commands.map((item) => (
        <ShellCommandButton
          key={item.id}
          item={item}
          focusedCommandIdRef={focusedCommandIdRef}
          onCommandElementChange={onCommandElementChange}
        />
      ))}
    </div>
  );
}

function setCommandElement(
  item: ShellCommand,
  element: HTMLElement | null,
  onCommandElementChange?: TopBarProps["onCommandElementChange"],
) {
  if (item.focusRef) {
    if (element || item.focusRef.current) item.focusRef.current = element;
  }
  onCommandElementChange?.(item.id, element);
}

function ShellCommandButton({
  item,
  focusedCommandIdRef,
  onCommandElementChange,
}: {
  item: ShellCommand;
  focusedCommandIdRef: RefObject<string | null>;
  onCommandElementChange?: TopBarProps["onCommandElementChange"];
}) {
  const Icon = item.icon;
  const style = {
    "--shell-command-width": `${commandFieldWidth(item)}px`,
  } as CSSProperties;
  const commonProps = {
    ref: (element: HTMLButtonElement | null) =>
      setCommandElement(item, element, onCommandElementChange),
    type: "button" as const,
    variant: "ghost" as const,
    size: "icon-sm" as const,
    className: "app-shell-command",
    style,
    "data-shell-command": item.id,
    "data-top-bar-action": item.id,
    "data-command-presentation": item.presentation,
    "aria-label": item.label,
    "aria-pressed": item.pressed,
    "aria-controls": item.controls,
    "aria-expanded": item.expanded,
    disabled: item.disabled,
    onFocus: () => {
      focusedCommandIdRef.current = item.id;
    },
    onClick: item.command,
  };
  if (item.presentation === "icon") {
    return (
      <IconActionButton
        {...commonProps}
        tooltip={item.label}
        tooltipSide="bottom"
      >
        <Icon aria-hidden="true" />
      </IconActionButton>
    );
  }

  return (
    <Button {...commonProps}>
      <Icon aria-hidden="true" />
      <span className="app-shell-command-label">{item.label}</span>
    </Button>
  );
}

function OverflowMenu({
  commands,
  triggerRef,
  focusedCommandIdRef,
  pendingOverflowFocusIdRef,
  onCommandElementChange,
}: {
  commands: Array<ShellCommand>;
  triggerRef: RefObject<HTMLButtonElement | null>;
  focusedCommandIdRef: RefObject<string | null>;
  pendingOverflowFocusIdRef: RefObject<string | null>;
  onCommandElementChange?: TopBarProps["onCommandElementChange"];
}) {
  const itemElementsRef = useRef(new Map<string, HTMLElement>());

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <IconActionButton
            ref={triggerRef}
            type="button"
            variant="ghost"
            size="icon-sm"
            className="app-shell-command"
            tooltip="More actions"
            tooltipSide="bottom"
            data-shell-overflow-trigger
          >
            <MoreHorizontal aria-hidden="true" />
          </IconActionButton>
        }
      />
      <DropdownMenuContent align="end">
        {commands.map((item) => {
          const Icon = item.icon;
          return (
            <DropdownMenuCheckboxItem
              key={item.id}
              ref={(element) => {
                if (element) itemElementsRef.current.set(item.id, element);
                else itemElementsRef.current.delete(item.id);
                setCommandElement(item, element, onCommandElementChange);
              }}
              disabled={item.disabled}
              checked={item.pressed}
              data-shell-command={item.id}
              data-top-bar-action={item.id}
              onFocus={() => {
                focusedCommandIdRef.current = item.id;
              }}
              onClick={item.command}
            >
              <Icon aria-hidden="true" />
              {item.label}
            </DropdownMenuCheckboxItem>
          );
        })}
        <OverflowFocusTarget
          pendingOverflowFocusIdRef={pendingOverflowFocusIdRef}
          itemElementsRef={itemElementsRef}
        />
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function OverflowFocusTarget({
  pendingOverflowFocusIdRef,
  itemElementsRef,
}: {
  pendingOverflowFocusIdRef: RefObject<string | null>;
  itemElementsRef: RefObject<Map<string, HTMLElement>>;
}) {
  useLayoutEffect(() => {
    const pendingId = pendingOverflowFocusIdRef.current;
    if (!pendingId) return;
    requestAnimationFrame(() => {
      itemElementsRef.current.get(pendingId)?.focus();
      pendingOverflowFocusIdRef.current = null;
    });
  }, [itemElementsRef, pendingOverflowFocusIdRef]);

  return null;
}
