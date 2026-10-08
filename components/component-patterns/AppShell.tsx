"use client";

// File: components/component-patterns/AppShell.tsx

import { useDirection } from "../component-core/direction";
import {
  createContext,
  useContext,
  useId,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import { shellMetrics } from "../lib/metrics";

import {
  MAX_SIDEBAR_WIDTH,
  MIN_SIDEBAR_WIDTH,
  Sidebar,
  useSidebarController,
} from "./Sidebar";
import { TopBar, resolveShellContributions } from "./TopBar";

import type { ShellPrimaryContribution, ShellTabsContribution } from "./TopBar";
import type {
  MainContentShape,
  MainContentSurface,
  ShellCommand,
  ShellCommandAvailability,
  ShellCommandOverflow,
  SidebarMode,
} from "./shellContracts";
import type { LucideIcon } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

const MIN_MAIN_WIDTH = shellMetrics.mainContentMinWidth;
const DEFAULT_AUXILIARY_SIDEBAR_WIDTH = shellMetrics.auxiliaryDefaultWidth;
const MIN_AUXILIARY_SIDEBAR_WIDTH = shellMetrics.auxiliaryMinWidth;

export type AppShellContextValue = {
  mainContentShape: MainContentShape;
  mainContentSurface: MainContentSurface;
};

const AppShellContext = createContext<AppShellContextValue | null>(null);

export function useAppShell(): AppShellContextValue {
  const value = useContext(AppShellContext);
  if (!value) {
    throw new Error("useAppShell must be used within AppShell.");
  }
  return value;
}

export type AuxiliarySidebarContribution = {
  id: string;
  ownerId: string;
  label: string;
  icon: LucideIcon;
  order: number;
  priority: number;
  overflow: ShellCommandOverflow;
  availability: ShellCommandAvailability;
  disabled: boolean;
  presentation: ShellCommand["presentation"];
  widthUnits: number;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean, reason: AuxiliarySidebarChangeReason) => void;
  content: ReactNode;
};

export type AuxiliarySidebarChangeReason =
  "trigger" | "close-button" | "width-loss" | "owner-change";

export type AppShellProps = {
  primaryContributions: Array<ShellPrimaryContribution>;
  navigationCommands: Array<ShellCommand>;
  viewCommands: Array<ShellCommand>;
  mainContextCommands: Array<ShellCommand>;
  trailingCommands: Array<ShellCommand>;
  tabs?: ShellTabsContribution;
  leftSidebarCapabilities?: Array<ShellCommand>;
  auxiliarySidebar?: AuxiliarySidebarContribution;
  availableCommandWidthUnits?: number;
  leftSidebar: ReactNode;
  rightSidebar?: ReactNode;
  leftSidebarHeader?: ReactNode;
  rightSidebarHeader?: ReactNode;
  leftSidebarLabel?: string;
  rightSidebarLabel?: string;
  mainContentShape?: MainContentShape;
  mainContentSurface?: MainContentSurface;
  /** `'none'` pins the pane docked and hides its trigger and handle. */
  leftSidebarChrome?: "trigger" | "none";
  /** Top-strip content rendered only without a top bar. */
  windowGrip?: ReactNode;
  children: ReactNode;
  leftSidebarMode?: SidebarMode;
  rightSidebarMode?: SidebarMode;
  defaultLeftSidebarMode?: SidebarMode;
  defaultRightSidebarMode?: SidebarMode;
  defaultLeftSidebarWidth?: number;
  defaultRightSidebarWidth?: number;
  onLeftSidebarModeChange?: (mode: SidebarMode) => void;
  onRightSidebarModeChange?: (mode: SidebarMode) => void;
};

export function AppShell({
  primaryContributions,
  navigationCommands,
  viewCommands,
  mainContextCommands,
  trailingCommands,
  tabs,
  leftSidebarCapabilities = [],
  auxiliarySidebar,
  availableCommandWidthUnits,
  leftSidebar,
  rightSidebar,
  leftSidebarChrome = "trigger",
  windowGrip,
  leftSidebarHeader,
  rightSidebarHeader,
  leftSidebarLabel = "Left sidebar",
  rightSidebarLabel = "Right sidebar",
  mainContentShape = "document",
  mainContentSurface = "paper",
  children,
  leftSidebarMode,
  rightSidebarMode,
  defaultLeftSidebarMode,
  defaultRightSidebarMode,
  defaultLeftSidebarWidth,
  defaultRightSidebarWidth,
  onLeftSidebarModeChange,
  onRightSidebarModeChange,
}: AppShellProps) {
  const direction = useDirection();
  const instanceId = useId().replace(/:/g, "");
  const shellId = `app-shell-${instanceId}`;
  const leftSidebarId = `${shellId}-left-sidebar`;
  const rightSidebarId = `${shellId}-right-sidebar`;
  const hasRightSidebar = rightSidebar !== undefined;
  const hasTopBar =
    primaryContributions.length > 0 ||
    navigationCommands.length > 0 ||
    viewCommands.length > 0 ||
    mainContextCommands.length > 0 ||
    trailingCommands.length > 0 ||
    tabs !== undefined ||
    leftSidebarCapabilities.length > 0 ||
    hasRightSidebar ||
    leftSidebarChrome !== "none";

  if (
    !hasRightSidebar &&
    (rightSidebarMode !== undefined ||
      defaultRightSidebarMode !== undefined ||
      defaultRightSidebarWidth !== undefined ||
      onRightSidebarModeChange !== undefined)
  ) {
    throw new Error(
      "Shell was given right sidebar options without a right sidebar.",
    );
  }
  const mainContentId = `${shellId}-main-content`;
  const auxiliaryPanelId = `${shellId}-auxiliary-panel`;
  const layoutRef = useRef<HTMLDivElement>(null);
  const leftTriggerRef = useRef<HTMLButtonElement>(null);
  const rightTriggerRef = useRef<HTMLButtonElement>(null);
  const mainContentRef = useRef<HTMLElement>(null);
  const auxiliaryTriggerRef = useRef<HTMLElement>(null);
  const auxiliaryHadFocusRef = useRef(false);
  const [layoutWidth, setLayoutWidth] = useState(() =>
    typeof window === "undefined" ? 0 : window.innerWidth,
  );
  const [uncontrolledAuxiliaryOpen, setUncontrolledAuxiliaryOpen] = useState(
    auxiliarySidebar?.defaultOpen ?? false,
  );
  const auxiliaryOwnerKey = auxiliarySidebar
    ? `${auxiliarySidebar.id}:${auxiliarySidebar.ownerId}`
    : "";
  const [acceptedAuxiliaryOwnerKey, setAcceptedAuxiliaryOwnerKey] =
    useState(auxiliaryOwnerKey);
  const [blockedControlledOwnerKey, setBlockedControlledOwnerKey] = useState<
    string | null
  >(null);
  const previousAuxiliaryRef = useRef({
    ownerKey: auxiliaryOwnerKey,
    open: auxiliarySidebar?.open ?? auxiliarySidebar?.defaultOpen ?? false,
    onOpenChange: auxiliarySidebar?.onOpenChange,
  });
  const previousAuxiliaryAvailableRef = useRef(false);
  const topBarCapabilityElementsRef = useRef(new Map<string, HTMLElement>());
  const sidebarCapabilityElementsRef = useRef(new Map<string, HTMLElement>());
  const pendingCapabilityFocusRef = useRef<{
    id: string;
    surface: "topbar" | "sidebar";
  } | null>(null);

  useLayoutEffect(() => {
    const layout = layoutRef.current;
    if (!layout) return;
    const initialWidth = layout.getBoundingClientRect().width;
    if (initialWidth > 0) setLayoutWidth(initialWidth);
    const observer = new ResizeObserver(([entry]) => {
      setLayoutWidth(entry.contentRect.width);
    });
    observer.observe(layout);
    return () => observer.disconnect();
  }, []);

  const left = useSidebarController({
    side: "left",
    layoutRef,
    triggerRef: leftTriggerRef,
    maxWidth: MAX_SIDEBAR_WIDTH,
    mode: leftSidebarChrome === "none" ? "docked" : leftSidebarMode,
    defaultMode: defaultLeftSidebarMode,
    defaultWidth: defaultLeftSidebarWidth,
    onModeChange: onLeftSidebarModeChange,
  });
  const rightMaximum =
    layoutWidth === 0
      ? MAX_SIDEBAR_WIDTH
      : Math.max(
          MIN_SIDEBAR_WIDTH,
          Math.min(
            layoutWidth - (left.isDocked ? left.width : 0) - MIN_MAIN_WIDTH,
            MAX_SIDEBAR_WIDTH,
          ),
        );
  const right = useSidebarController({
    side: "right",
    layoutRef,
    triggerRef: rightTriggerRef,
    minWidth: MIN_SIDEBAR_WIDTH,
    maxWidth: rightMaximum,
    // Controller call preserves hook order for an absent pane.
    mode: hasRightSidebar ? rightSidebarMode : "closed",
    defaultMode: defaultRightSidebarMode,
    defaultWidth: defaultRightSidebarWidth,
    onModeChange: onRightSidebarModeChange,
  });

  const maximumAuxiliaryWidth =
    layoutWidth === 0
      ? DEFAULT_AUXILIARY_SIDEBAR_WIDTH
      : layoutWidth -
        (left.isDocked ? left.width : 0) -
        (right.isDocked ? right.width : 0) -
        MIN_MAIN_WIDTH;
  const auxiliaryAvailable = Boolean(
    auxiliarySidebar &&
    auxiliarySidebar.availability === "available" &&
    maximumAuxiliaryWidth >= MIN_AUXILIARY_SIDEBAR_WIDTH,
  );
  const auxiliaryWidth = Math.min(
    DEFAULT_AUXILIARY_SIDEBAR_WIDTH,
    maximumAuxiliaryWidth,
  );
  const ownerAccepted = acceptedAuxiliaryOwnerKey === auxiliaryOwnerKey;
  const requestedAuxiliaryOpen =
    auxiliarySidebar?.open ?? uncontrolledAuxiliaryOpen;
  const auxiliaryOpen = Boolean(
    auxiliarySidebar &&
    ownerAccepted &&
    requestedAuxiliaryOpen &&
    auxiliaryAvailable &&
    blockedControlledOwnerKey !== auxiliaryOwnerKey,
  );

  const restoreAuxiliaryFocus = (preferTrigger: boolean) => {
    requestAnimationFrame(() => {
      const target = preferTrigger
        ? (auxiliaryTriggerRef.current ?? mainContentRef.current)
        : mainContentRef.current;
      target?.focus();
      auxiliaryHadFocusRef.current = false;
    });
  };
  const setAuxiliaryOpen = (
    open: boolean,
    reason: AuxiliarySidebarChangeReason,
  ) => {
    if (auxiliarySidebar?.open === undefined) {
      setUncontrolledAuxiliaryOpen(open);
    }
    auxiliarySidebar?.onOpenChange?.(open, reason);
    if (!open && (reason === "close-button" || auxiliaryHadFocusRef.current)) {
      restoreAuxiliaryFocus(reason === "close-button");
    }
  };

  useLayoutEffect(() => {
    if (acceptedAuxiliaryOwnerKey === auxiliaryOwnerKey) return;
    const previous = previousAuxiliaryRef.current;
    if (previous.open) previous.onOpenChange?.(false, "owner-change");
    if (previous.open && auxiliarySidebar?.open !== undefined) {
      setBlockedControlledOwnerKey(auxiliaryOwnerKey);
    }
    setUncontrolledAuxiliaryOpen(false);
    setAcceptedAuxiliaryOwnerKey(auxiliaryOwnerKey);
    if (auxiliaryHadFocusRef.current) restoreAuxiliaryFocus(false);
  }, [acceptedAuxiliaryOwnerKey, auxiliaryOwnerKey]);

  useLayoutEffect(() => {
    if (
      blockedControlledOwnerKey === auxiliaryOwnerKey &&
      auxiliarySidebar?.open === false
    ) {
      setBlockedControlledOwnerKey(null);
    }
  }, [auxiliaryOwnerKey, auxiliarySidebar?.open, blockedControlledOwnerKey]);

  useLayoutEffect(() => {
    if (
      ownerAccepted &&
      requestedAuxiliaryOpen &&
      previousAuxiliaryAvailableRef.current &&
      !auxiliaryAvailable
    ) {
      setAuxiliaryOpen(false, "width-loss");
    }
    previousAuxiliaryAvailableRef.current = auxiliaryAvailable;
  }, [auxiliaryAvailable, ownerAccepted, requestedAuxiliaryOpen]);

  useLayoutEffect(() => {
    previousAuxiliaryRef.current = {
      ownerKey: auxiliaryOwnerKey,
      open: requestedAuxiliaryOpen,
      onOpenChange: auxiliarySidebar?.onOpenChange,
    };
  });

  const capabilityIds = new Set(leftSidebarCapabilities.map(({ id }) => id));
  const setCapabilityElement = (
    surface: "topbar" | "sidebar",
    id: string,
    element: HTMLElement | null,
  ) => {
    if (!capabilityIds.has(id)) return;
    const elements =
      surface === "topbar"
        ? topBarCapabilityElementsRef.current
        : sidebarCapabilityElementsRef.current;
    if (element) elements.set(id, element);
    else elements.delete(id);
  };
  const captureCapabilityFocus = (surface: "topbar" | "sidebar") => {
    const source =
      surface === "topbar"
        ? topBarCapabilityElementsRef.current
        : sidebarCapabilityElementsRef.current;
    for (const [id, element] of source) {
      if (element === document.activeElement) {
        pendingCapabilityFocusRef.current = {
          id,
          surface: surface === "topbar" ? "sidebar" : "topbar",
        };
        return;
      }
    }
  };

  useLayoutEffect(() => {
    const pending = pendingCapabilityFocusRef.current;
    if (!pending) return;
    const expectedSurface = left.mode === "closed" ? "topbar" : "sidebar";
    if (pending.surface !== expectedSurface) return;
    const elements =
      expectedSurface === "topbar"
        ? topBarCapabilityElementsRef.current
        : sidebarCapabilityElementsRef.current;
    const target = elements.get(pending.id);
    if (!target) return;
    target.focus();
    pendingCapabilityFocusRef.current = null;
  }, [left.mode]);

  const auxiliaryCommand: ShellCommand | null = auxiliarySidebar
    ? {
        id: `${auxiliarySidebar.id}.toggle`,
        label: `Open ${auxiliarySidebar.label}`,
        icon: auxiliarySidebar.icon,
        order: auxiliarySidebar.order,
        priority: auxiliarySidebar.priority,
        overflow: auxiliarySidebar.overflow,
        availability: auxiliaryAvailable ? "available" : "unavailable",
        disabled: auxiliarySidebar.disabled,
        pressed: auxiliaryOpen,
        presentation: auxiliarySidebar.presentation,
        widthUnits: auxiliarySidebar.widthUnits,
        focusRef: auxiliaryTriggerRef,
        controls: auxiliaryPanelId,
        expanded: auxiliaryOpen,
        command: () => setAuxiliaryOpen(!auxiliaryOpen, "trigger"),
      }
    : null;
  const commandWidthUnits =
    availableCommandWidthUnits ??
    (layoutWidth === 0
      ? 10
      : layoutWidth >= 1200
        ? 15
        : layoutWidth >= 1000
          ? 9
          : 7);
  const resolved = resolveShellContributions({
    primaryContributions,
    navigationCommands,
    capabilityCommands: left.mode === "closed" ? leftSidebarCapabilities : [],
    // Leading width uses full capability set in every pane state.
    reservedCapabilityCommands: leftSidebarCapabilities,
    viewCommands: auxiliaryCommand
      ? [...viewCommands, auxiliaryCommand]
      : viewCommands,
    mainContextCommands,
    trailingCommands,
    tabs,
    availableCommandWidthUnits: commandWidthUnits,
  });
  const sidebarCapabilities = leftSidebarCapabilities
    .filter((item) => item.availability === "available")
    .sort(
      (leftItem, rightItem) =>
        leftItem.order - rightItem.order ||
        leftItem.id.localeCompare(rightItem.id),
    );

  const shellStyle = {
    "--left-sidebar-width": `${left.width}px`,
    "--left-docked-width": left.isDocked ? "var(--left-sidebar-width)" : "0px",
    "--right-sidebar-width": `${right.width}px`,
    "--right-docked-width": right.isDocked
      ? "var(--right-sidebar-width)"
      : "0px",
    "--auxiliary-panel-width": auxiliaryOpen ? `${auxiliaryWidth}px` : "0px",
    "--main-content-min-width": `${MIN_MAIN_WIDTH}px`,
    "--command-rail-width": `${resolved.commandRailWidth}px`,
  } as CSSProperties;

  const shell = (
    <div
      id={shellId}
      className="app-shell"
      dir={direction}
      style={shellStyle}
      data-left-mode={left.mode}
      data-right-mode={right.mode}
      data-right-chrome={hasRightSidebar ? undefined : "none"}
      data-left-chrome={leftSidebarChrome}
      data-top-bar={hasTopBar ? undefined : "none"}
      data-main-content-shape={mainContentShape}
      data-main-content-surface={mainContentSurface}
      data-left-resizing={left.isResizing}
      data-right-resizing={right.isResizing}
      data-left-snap={left.resizePhase ?? undefined}
      data-right-snap={right.resizePhase ?? undefined}
    >
      {!hasTopBar && windowGrip ? (
        <div className="app-shell-window-grip">{windowGrip}</div>
      ) : null}
      {hasTopBar ? (
        <TopBar
          direction={direction}
          {...resolved}
          leftSidebarControl={
            leftSidebarChrome === "none"
              ? undefined
              : {
                  side: "left",
                  mode: left.mode,
                  controls: leftSidebarId,
                  triggerRef: leftTriggerRef,
                  onPointerEnter: () => {
                    captureCapabilityFocus("topbar");
                    left.openPreview();
                  },
                  onPointerLeave: left.schedulePreviewClose,
                  onClick: () => {
                    captureCapabilityFocus(
                      left.mode === "closed" ? "topbar" : "sidebar",
                    );
                    left.toggleDocked();
                  },
                }
          }
          rightSidebarControl={
            hasRightSidebar
              ? {
                  side: "right",
                  mode: right.mode,
                  controls: rightSidebarId,
                  triggerRef: rightTriggerRef,
                  onPointerEnter: right.openPreview,
                  onPointerLeave: right.schedulePreviewClose,
                  onClick: right.toggleDocked,
                }
              : undefined
          }
          onCommandElementChange={(id, element) =>
            setCapabilityElement("topbar", id, element)
          }
        />
      ) : null}

      <div ref={layoutRef} className="app-shell-body" dir="ltr">
        <Sidebar
          variant="universal"
          id={leftSidebarId}
          side="left"
          label={leftSidebarLabel}
          controller={left}
          direction={direction}
          mainContentId={mainContentId}
          header={leftSidebarHeader}
          chromeOffset={resolved.leadingChromeOffset}
          capabilities={sidebarCapabilities}
          onCapabilityElementChange={(id, element) =>
            setCapabilityElement("sidebar", id, element)
          }
        >
          {leftSidebar}
        </Sidebar>

        <main
          ref={mainContentRef}
          id={mainContentId}
          className="app-shell-main-content"
          dir={direction}
          tabIndex={-1}
        >
          {mainContentShape === "document" ? (
            <div className="app-document">
              <div className="app-paper">{children}</div>
            </div>
          ) : (
            children
          )}
        </main>

        {auxiliaryOpen && auxiliarySidebar ? (
          <Sidebar
            variant="auxiliary"
            id={auxiliaryPanelId}
            side="right"
            label={auxiliarySidebar.label}
            direction={direction}
            onClose={() => setAuxiliaryOpen(false, "close-button")}
            onFocusCapture={() => {
              auxiliaryHadFocusRef.current = true;
            }}
            onBlurCapture={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) {
                auxiliaryHadFocusRef.current = false;
              }
            }}
          >
            {auxiliarySidebar.content}
          </Sidebar>
        ) : null}

        {hasRightSidebar ? (
          <Sidebar
            variant="universal"
            id={rightSidebarId}
            side="right"
            label={rightSidebarLabel}
            controller={right}
            direction={direction}
            mainContentId={mainContentId}
            header={rightSidebarHeader}
          >
            {rightSidebar}
          </Sidebar>
        ) : null}
      </div>
    </div>
  );

  return (
    <AppShellContext.Provider value={{ mainContentShape, mainContentSurface }}>
      {shell}
    </AppShellContext.Provider>
  );
}
