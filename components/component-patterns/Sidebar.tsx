"use client";

// File: components/component-patterns/Sidebar.tsx

import { Button } from "../component-elements/button";
import { X } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { interactionMetrics, sidebarMetrics } from "../lib/metrics";

import { IconActionButton } from "./IconActionButton";

import type { ShellCommand, SidebarMode, SidebarSide } from "./shellContracts";
import type {
  CSSProperties,
  FocusEventHandler,
  KeyboardEvent,
  ReactNode,
  PointerEvent as ReactPointerEvent,
  RefObject,
  SetStateAction,
  TransitionEvent,
} from "react";

export const DEFAULT_SIDEBAR_WIDTH = sidebarMetrics.defaultWidth;
export const MIN_SIDEBAR_WIDTH = sidebarMetrics.minWidth;
export const MAX_SIDEBAR_WIDTH = sidebarMetrics.maxWidth;
const PREVIEW_CLOSE_GRACE_MS = interactionMetrics.sidebarPreviewCloseGrace;

type ResizePhase = "closing" | "recovering" | null;

const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max);

type Point = { x: number; y: number };

const rectangleCorners = ({
  left,
  right,
  top,
  bottom,
}: Pick<DOMRect, "left" | "right" | "top" | "bottom">): Array<Point> => [
  { x: left, y: top },
  { x: right, y: top },
  { x: right, y: bottom },
  { x: left, y: bottom },
];

const cross = (origin: Point, a: Point, b: Point) =>
  (a.x - origin.x) * (b.y - origin.y) - (a.y - origin.y) * (b.x - origin.x);

/** Preview transit includes the gap between trigger and pane. */
function previewTransitContains(point: Point, trigger: DOMRect, pane: DOMRect) {
  const points = [...rectangleCorners(trigger), ...rectangleCorners(pane)].sort(
    (a, b) => a.x - b.x || a.y - b.y,
  );
  const lower: Array<Point> = [];
  for (const candidate of points) {
    while (
      lower.length >= 2 &&
      cross(lower[lower.length - 2], lower[lower.length - 1], candidate) <= 0
    ) {
      lower.pop();
    }
    lower.push(candidate);
  }
  const upper: Array<Point> = [];
  for (const candidate of [...points].reverse()) {
    while (
      upper.length >= 2 &&
      cross(upper[upper.length - 2], upper[upper.length - 1], candidate) <= 0
    ) {
      upper.pop();
    }
    upper.push(candidate);
  }
  const hull = [...lower.slice(0, -1), ...upper.slice(0, -1)];

  let direction = 0;
  for (let index = 0; index < hull.length; index += 1) {
    const turn = cross(hull[index], hull[(index + 1) % hull.length], point);
    if (turn === 0) continue;
    const nextDirection = Math.sign(turn);
    if (direction !== 0 && direction !== nextDirection) return false;
    direction = nextDirection;
  }
  return true;
}

export type SidebarControllerOptions = {
  side: SidebarSide;
  layoutRef: RefObject<HTMLDivElement | null>;
  triggerRef: RefObject<HTMLButtonElement | null>;
  minWidth?: number;
  maxWidth: number;
  mode?: SidebarMode;
  defaultMode?: SidebarMode;
  defaultWidth?: number;
  onModeChange?: (mode: SidebarMode) => void;
};

export function useSidebarController({
  side,
  layoutRef,
  triggerRef,
  minWidth = MIN_SIDEBAR_WIDTH,
  maxWidth,
  mode: controlledMode,
  defaultMode = "closed",
  defaultWidth = DEFAULT_SIDEBAR_WIDTH,
  onModeChange,
}: SidebarControllerOptions) {
  const [uncontrolledMode, setUncontrolledMode] =
    useState<SidebarMode>(defaultMode);
  const [dragCommittedClosed, setDragCommittedClosed] = useState(false);
  const mode = dragCommittedClosed
    ? "closed"
    : (controlledMode ?? uncontrolledMode);
  const setMode = (next: SetStateAction<SidebarMode>) => {
    const nextMode = typeof next === "function" ? next(mode) : next;
    if (controlledMode === undefined) setUncontrolledMode(nextMode);
    onModeChange?.(nextMode);
  };
  const [width, setWidth] = useState(() =>
    clamp(defaultWidth, minWidth, maxWidth),
  );
  const [isResizing, setIsResizing] = useState(false);
  const [dragCollapsed, setDragCollapsed] = useState(false);
  const [resizePhase, setResizePhase] = useState<ResizePhase>(null);
  const paneRef = useRef<HTMLElement>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finishResizeRef = useRef<(() => void) | null>(null);
  const pointerHeldRef = useRef(false);
  const commitAfterCloseRef = useRef(false);
  const dragCollapsedRef = useRef(false);
  const closingRef = useRef(false);
  const recoveringRef = useRef(false);
  const latestRawWidthRef = useRef<number>(DEFAULT_SIDEBAR_WIDTH);
  const resizeStartWidthRef = useRef<number>(DEFAULT_SIDEBAR_WIDTH);
  const minWidthRef = useRef(minWidth);
  const maxWidthRef = useRef(maxWidth);
  minWidthRef.current = minWidth;
  maxWidthRef.current = maxWidth;

  useEffect(() => {
    if (!dragCommittedClosed || controlledMode === undefined) return;
    setDragCommittedClosed(false);
    setDragCollapsed(false);
  }, [controlledMode, dragCommittedClosed]);

  const cancelPreviewClose = () => {
    if (closeTimerRef.current === null) return;
    clearTimeout(closeTimerRef.current);
    closeTimerRef.current = null;
  };

  const isWithinPreviewTransit = (clientX: number, clientY: number) => {
    const trigger = triggerRef.current;
    const pane = paneRef.current;
    if (!trigger || !pane) return false;
    return previewTransitContains(
      { x: clientX, y: clientY },
      trigger.getBoundingClientRect(),
      pane.getBoundingClientRect(),
    );
  };

  const clearCollapseLatch = () => {
    finishResizeRef.current = null;
    commitAfterCloseRef.current = false;
    setDragCommittedClosed(false);
    dragCollapsedRef.current = false;
    closingRef.current = false;
    recoveringRef.current = false;
    setDragCollapsed(false);
    setResizePhase(null);
  };

  const openPreview = () => {
    cancelPreviewClose();
    if (mode === "closed") clearCollapseLatch();
    setMode((current) => (current === "closed" ? "preview" : current));
  };

  const schedulePreviewClose = (
    event?: Pick<ReactPointerEvent<HTMLElement>, "clientX" | "clientY">,
  ) => {
    if (event && isWithinPreviewTransit(event.clientX, event.clientY)) {
      cancelPreviewClose();
      return;
    }
    if (closeTimerRef.current !== null) return;
    closeTimerRef.current = setTimeout(() => {
      closeTimerRef.current = null;
      if (paneRef.current?.contains(document.activeElement)) return;
      setMode((current) => (current === "preview" ? "closed" : current));
    }, PREVIEW_CLOSE_GRACE_MS);
  };

  useEffect(() => {
    if (mode !== "preview") return;
    const onPointerMove = (event: PointerEvent) => {
      if (isWithinPreviewTransit(event.clientX, event.clientY)) {
        cancelPreviewClose();
        return;
      }
      schedulePreviewClose();
    };
    document.addEventListener("pointermove", onPointerMove, true);
    return () =>
      document.removeEventListener("pointermove", onPointerMove, true);
  }, [mode, isWithinPreviewTransit, cancelPreviewClose, schedulePreviewClose]);

  const toggleDocked = () => {
    cancelPreviewClose();
    if (mode === "docked") {
      setMode("closed");
      return;
    }
    clearCollapseLatch();
    setMode("docked");
  };

  useEffect(
    () => () => {
      if (closeTimerRef.current !== null) clearTimeout(closeTimerRef.current);
      finishResizeRef.current = null;
    },
    [],
  );

  useLayoutEffect(() => {
    if (!isResizing) return;

    const commitClosed = () => {
      finishResizeRef.current = null;
      commitAfterCloseRef.current = false;
      dragCollapsedRef.current = false;
      closingRef.current = false;
      recoveringRef.current = false;
      setDragCommittedClosed(true);
      setMode("closed");
      setWidth(resizeStartWidthRef.current);
      setResizePhase(null);
      requestAnimationFrame(() => triggerRef.current?.focus());
    };

    function beginClosing() {
      recoveringRef.current = false;
      closingRef.current = true;
      dragCollapsedRef.current = true;
      setDragCollapsed(true);
      setResizePhase("closing");

      finishResizeRef.current = () => {
        if (!closingRef.current) return;
        finishResizeRef.current = null;
        closingRef.current = false;
        setResizePhase(null);
        setMode("closed");

        if (commitAfterCloseRef.current || !pointerHeldRef.current) {
          commitClosed();
          return;
        }
        if (latestRawWidthRef.current > minWidthRef.current / 2) {
          beginRecovery();
        }
      };
    }

    function beginRecovery() {
      closingRef.current = false;
      dragCollapsedRef.current = false;
      recoveringRef.current = true;
      setDragCommittedClosed(false);
      setMode("docked");
      setDragCollapsed(false);
      setWidth(minWidthRef.current);
      setResizePhase("recovering");

      finishResizeRef.current = () => {
        if (!recoveringRef.current) return;
        finishResizeRef.current = null;
        recoveringRef.current = false;
        setWidth(
          clamp(
            latestRawWidthRef.current,
            minWidthRef.current,
            maxWidthRef.current,
          ),
        );
        setResizePhase(null);

        if (
          pointerHeldRef.current &&
          latestRawWidthRef.current <= minWidthRef.current / 2
        ) {
          beginClosing();
        }
      };
    }

    const handlePointerMove = (event: PointerEvent) => {
      const layout = layoutRef.current;
      if (!layout) return;
      const bounds = layout.getBoundingClientRect();
      const rawWidth =
        side === "left"
          ? event.clientX - bounds.left
          : bounds.right - event.clientX;
      latestRawWidthRef.current = rawWidth;

      if (closingRef.current || recoveringRef.current) return;
      if (dragCollapsedRef.current) {
        if (rawWidth > minWidthRef.current / 2) beginRecovery();
        return;
      }
      if (rawWidth <= minWidthRef.current / 2) {
        beginClosing();
        return;
      }
      setWidth(clamp(rawWidth, minWidthRef.current, maxWidthRef.current));
    };

    const stopResizing = () => {
      if (!pointerHeldRef.current) return;
      pointerHeldRef.current = false;

      if (closingRef.current || recoveringRef.current) {
        if (closingRef.current) commitAfterCloseRef.current = true;
        setIsResizing(false);
        return;
      }
      if (dragCollapsedRef.current) {
        commitClosed();
        setIsResizing(false);
        return;
      }

      setWidth(
        clamp(
          latestRawWidthRef.current,
          minWidthRef.current,
          maxWidthRef.current,
        ),
      );
      finishResizeRef.current = null;
      setResizePhase(null);
      setIsResizing(false);
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    window.addEventListener("pointercancel", stopResizing);
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      window.removeEventListener("pointercancel", stopResizing);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  }, [isResizing, layoutRef, side, triggerRef]);

  const startResizing = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.tabIndex < 0) return;
    event.preventDefault();
    finishResizeRef.current = null;
    commitAfterCloseRef.current = false;
    setDragCommittedClosed(false);
    const effectiveWidth = Math.min(width, maxWidth);
    resizeStartWidthRef.current = effectiveWidth;
    latestRawWidthRef.current = effectiveWidth;
    dragCollapsedRef.current = false;
    closingRef.current = false;
    recoveringRef.current = false;
    pointerHeldRef.current = true;
    setDragCollapsed(false);
    setResizePhase(null);
    setIsResizing(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handleResizeKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (mode !== "docked" || resizePhase !== null) return;
    const outwardKey = side === "left" ? "ArrowRight" : "ArrowLeft";
    const inwardKey = side === "left" ? "ArrowLeft" : "ArrowRight";
    let nextWidth: number | null = null;

    if (event.key === outwardKey) nextWidth = width + 16;
    if (event.key === inwardKey) nextWidth = width - 16;
    if (event.key === "Home") nextWidth = minWidth;
    if (event.key === "End") nextWidth = maxWidth;
    if (event.key === "Enter") {
      event.preventDefault();
      setMode("closed");
      requestAnimationFrame(() => triggerRef.current?.focus());
      return;
    }
    if (nextWidth === null) return;
    event.preventDefault();
    setWidth(clamp(nextWidth, minWidth, maxWidth));
  };

  const finishResize = (event: TransitionEvent<HTMLElement>) => {
    if (
      event.target === event.currentTarget &&
      event.propertyName === "width"
    ) {
      finishResizeRef.current?.();
    }
  };

  return {
    mode,
    minWidth,
    maxWidth,
    width: dragCollapsed ? 0 : Math.min(width, maxWidth),
    isOpen: mode !== "closed",
    isDocked: mode === "docked",
    isResizing,
    resizePhase,
    paneRef,
    cancelPreviewClose,
    openPreview,
    schedulePreviewClose,
    toggleDocked,
    startResizing,
    handleResizeKey,
    finishResize,
  };
}

export type SidebarController = ReturnType<typeof useSidebarController>;

type SidebarCommonProps = {
  id: string;
  side: SidebarSide;
  label: string;
  direction: "ltr" | "rtl";
  header?: ReactNode;
  /** Shell chrome px beyond endpoint trigger. Zero without extra chrome. */
  chromeOffset?: number;
  children: ReactNode;
  onFocusCapture?: FocusEventHandler<HTMLElement>;
  onBlurCapture?: FocusEventHandler<HTMLElement>;
};

type UniversalSidebarProps = SidebarCommonProps & {
  variant: "universal";
  controller: SidebarController;
  mainContentId: string;
  capabilities?: Array<ShellCommand>;
  onCapabilityElementChange?: (id: string, element: HTMLElement | null) => void;
};

type AuxiliarySidebarProps = Omit<SidebarCommonProps, "side"> & {
  variant: "auxiliary";
  side: "right";
  onClose: () => void;
};

export type SidebarProps = UniversalSidebarProps | AuxiliarySidebarProps;

export function Sidebar(props: SidebarProps) {
  const { id, side, label, direction, header, chromeOffset, children } = props;
  const isUniversal = props.variant === "universal";
  const controller = isUniversal ? props.controller : null;
  const capabilities = isUniversal ? (props.capabilities ?? []) : [];
  const onCapabilityElementChange = isUniversal
    ? props.onCapabilityElementChange
    : undefined;
  const controls =
    isUniversal && side === "left"
      ? `${id} ${props.mainContentId}`
      : isUniversal
        ? `${props.mainContentId} ${id}`
        : undefined;

  return (
    <aside
      ref={controller?.paneRef}
      id={id}
      className={`app-sidebar app-sidebar-${props.variant} app-sidebar-${side}`}
      data-sidebar-variant={props.variant}
      style={
        chromeOffset
          ? ({
              "--app-sidebar-chrome-offset": `${chromeOffset}px`,
            } as CSSProperties)
          : undefined
      }
      data-narrow={
        controller && controller.width <= controller.minWidth ? "" : undefined
      }
      aria-label={label}
      aria-hidden={isUniversal && !controller?.isOpen}
      inert={isUniversal && !controller?.isOpen ? true : undefined}
      onPointerEnter={controller?.cancelPreviewClose}
      onPointerLeave={controller?.schedulePreviewClose}
      onFocusCapture={(event) => {
        controller?.cancelPreviewClose();
        props.onFocusCapture?.(event);
      }}
      onBlurCapture={(event) => {
        controller?.schedulePreviewClose();
        props.onBlurCapture?.(event);
      }}
      onTransitionEnd={controller?.finishResize}
    >
      {isUniversal && side === "right" ? (
        <SidebarResizeHandle
          side={side}
          controls={controls!}
          controller={controller!}
        />
      ) : null}
      <div
        className="app-sidebar-content"
        dir={direction}
        data-sidebar-header={header === null ? "none" : undefined}
      >
        {header === null ? null : (
          <div className="app-sidebar-header">
            <div className="app-sidebar-heading">
              {header === undefined ? <span>{label}</span> : header}
            </div>
            {!isUniversal ? (
              <IconActionButton
                type="button"
                variant="ghost"
                size="icon-sm"
                className="app-sidebar-close"
                tooltip={`Close ${label}`}
                onClick={props.onClose}
              >
                <X aria-hidden="true" />
              </IconActionButton>
            ) : null}
          </div>
        )}
        {capabilities.length > 0 ? (
          <div
            className="app-sidebar-capabilities"
            data-capability-presentation="labeled"
          >
            {capabilities.map((capability) => {
              const Icon = capability.icon;
              return (
                <Button
                  key={capability.id}
                  ref={(element) => {
                    if (capability.focusRef) {
                      capability.focusRef.current = element;
                    }
                    onCapabilityElementChange?.(capability.id, element);
                  }}
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="app-sidebar-capability"
                  data-shell-command={capability.id}
                  aria-pressed={capability.pressed}
                  aria-controls={capability.controls}
                  aria-expanded={capability.expanded}
                  disabled={capability.disabled}
                  onClick={capability.command}
                >
                  <Icon aria-hidden="true" className="size-4" />
                  {capability.label}
                </Button>
              );
            })}
          </div>
        ) : null}
        <div className="app-sidebar-scroll-content">{children}</div>
      </div>
      {isUniversal && side === "left" ? (
        <SidebarResizeHandle
          side={side}
          controls={controls!}
          controller={controller!}
        />
      ) : null}
    </aside>
  );
}

function SidebarResizeHandle({
  side,
  controls,
  controller,
}: {
  side: SidebarSide;
  controls: string;
  controller: SidebarController;
}) {
  return (
    <div
      className={`app-sidebar-resize-handle app-sidebar-resize-handle-${side}`}
      role="separator"
      tabIndex={controller.isDocked ? 0 : -1}
      aria-label={`Resize ${side} sidebar`}
      aria-orientation="vertical"
      aria-controls={controls}
      aria-valuemin={Math.round(controller.minWidth)}
      aria-valuemax={Math.round(controller.maxWidth)}
      aria-valuenow={Math.round(controller.width)}
      onPointerDown={controller.startResizing}
      onKeyDown={controller.handleResizeKey}
    />
  );
}
