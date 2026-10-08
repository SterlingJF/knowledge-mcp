"use client";

// File: components/component-elements/toaster.tsx

import {
  Toast,
  ToastClose,
  ToastContent,
  ToastDescription,
  ToastPortal,
  ToastProvider,
  ToastTitle,
  ToastViewport,
  createToastManager,
  toast,
  useToastManager,
} from "../component-core/toast";
import { cn } from "../lib/utils";

export type ToastPosition = "top-right" | "bottom-right";

/** Base UI has no position prop. Position is CSS on `Viewport` and `Root`. */
const VIEWPORT_POSITION = {
  "top-right": "top-[var(--app-bar-rail-inset)] bottom-auto",
  "bottom-right": "bottom-[var(--app-bar-rail-inset)] top-auto",
} satisfies Record<ToastPosition, string>;

const ROOT_POSITION = {
  "top-right": cn(
    "top-0 bottom-auto origin-top",
    "[--offset-y:calc(var(--toast-offset-y)+calc(var(--toast-index)*var(--gap))+var(--toast-swipe-movement-y))]",
    "after:top-auto after:bottom-full",
    "data-starting-style:[transform:translateY(-150%)]",
    "[&[data-ending-style]:not([data-limited]):not([data-swipe-direction])]:[transform:translateY(-150%)]",
  ),
  "bottom-right": "",
} satisfies Record<ToastPosition, string>;

/** Chrome scale. Base UI measures content into `--toast-height`. */
const TOAST_SCALE = cn("rounded-[var(--control-radius-md)]", "w-auto");
const TOAST_CONTENT_SCALE = "p-[var(--space-sm)]";

const SWIPE_DIRECTION = {
  "top-right": ["up", "right"],
  "bottom-right": ["down", "right"],
} satisfies Record<ToastPosition, Array<"up" | "down" | "left" | "right">>;

export type ToasterProps = {
  position?: ToastPosition;
  /** `0` disables automatic dismissal. */
  timeout?: number;
  limit?: number;
  children?: React.ReactNode;
};

export function Toaster({
  position = "top-right",
  timeout = 3000,
  limit = 1,
  children,
}: ToasterProps) {
  return (
    <ToastProvider toastManager={toast} timeout={timeout} limit={limit}>
      {children}
      <ToastPortal>
        <ToastViewport
          data-position={position}
          className={cn(
            "z-[var(--layer-overlay)]",
            VIEWPORT_POSITION[position],
          )}
        >
          <ToastList position={position} />
        </ToastViewport>
      </ToastPortal>
    </ToastProvider>
  );
}

function ToastList({ position }: { position: ToastPosition }) {
  const { toasts } = useToastManager();

  return toasts.map((item) => (
    <Toast
      key={item.id}
      toast={item}
      data-position={position}
      swipeDirection={SWIPE_DIRECTION[position]}
      className={cn(TOAST_SCALE, ROOT_POSITION[position])}
    >
      {/* Close control reserved for actionable toasts. */}
      <ToastContent className={TOAST_CONTENT_SCALE}>
        <div className="flex min-w-0 flex-1 flex-col gap-[var(--space-xxs)]">
          <ToastTitle />
          <ToastDescription />
        </div>
      </ToastContent>
    </Toast>
  ));
}

export {
  Toast,
  ToastClose,
  ToastContent,
  ToastDescription,
  ToastPortal,
  ToastProvider,
  ToastTitle,
  ToastViewport,
  createToastManager,
  toast,
  useToastManager,
};
