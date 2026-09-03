// File: launcher/src/component-elements/button.tsx
//
import { Button as ButtonBase, buttonVariants } from '@/component-core/button'
import { cn } from '@/lib/utils'

export function Button({
  className,
  variant = 'default',
  ...props
}: Parameters<typeof ButtonBase>[0]) {
  return (
    <ButtonBase
      variant={variant}
      className={cn(
        variant === 'default' &&
          'hover:bg-[color-mix(in_oklab,var(--primary),var(--primary-active)_52%)] active:bg-primary-active dark:hover:bg-[color-mix(in_srgb,var(--primary),var(--foreground)_20%)] dark:active:bg-primary-active',
        className,
      )}
      {...props}
    />
  )
}

export { buttonVariants }
