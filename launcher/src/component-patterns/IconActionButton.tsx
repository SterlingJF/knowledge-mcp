'use client'

// File: launcher/src/component-patterns/IconActionButton.tsx

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/component-core/tooltip'
import { Button } from '@/component-elements/button'
import { forwardRef } from 'react'

import type { ComponentProps } from 'react'

export type IconActionButtonProps = ComponentProps<typeof Button> & {
  tooltip: string
  tooltipSide?: ComponentProps<typeof TooltipContent>['side']
}

export const IconActionButton = forwardRef<
  HTMLButtonElement,
  IconActionButtonProps
>(function IconActionButton(
  { tooltip, tooltipSide, children, 'aria-label': ariaLabel, ...buttonProps },
  ref,
) {
  const label = tooltip.trim()
  if (!label) throw new Error('Icon action tooltips must not be empty.')

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className="inline-flex">
            <Button
              {...buttonProps}
              ref={ref}
              aria-label={ariaLabel ?? label}
              data-icon-action=""
              data-tooltip-label={label}
            >
              {children}
            </Button>
          </span>
        }
      />
      <TooltipContent side={tooltipSide}>{label}</TooltipContent>
    </Tooltip>
  )
})
