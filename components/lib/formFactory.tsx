// File: components/lib/formFactory.tsx
//

import { Input } from "../component-core/input";
import { Label } from "../component-core/label";
import { RadioGroup, RadioGroupItem } from "../component-core/radio-group";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "../component-core/select";
import { Button } from "../component-elements/button";
import { cn } from "../lib/utils";
import { createFormHook, createFormHookContexts } from "@tanstack/react-form";
import * as React from "react";

export const { fieldContext, formContext, useFieldContext } =
  createFormHookContexts();

type TextFieldProps = {
  label?: string;
  showLabel?: boolean;
  placeholder?: string;
};

function TextField({ label, placeholder, showLabel }: TextFieldProps) {
  const field = useFieldContext<string | undefined>();
  const id = React.useId();
  return (
    <div className="space-y-2">
      {label && showLabel && <Label htmlFor={id}>{label}</Label>}
      <Input
        id={id}
        value={field.state.value ?? ""}
        onChange={(e) => field.handleChange(e.target.value)}
        onBlur={field.handleBlur}
        placeholder={placeholder}
      />
      {field.state.meta.isTouched && !field.state.meta.isValid ? (
        <p className="text-sm text-destructive">
          {field.state.meta.errors.join(", ")}
        </p>
      ) : null}
    </div>
  );
}

type SelectFieldProps<T extends string> = {
  label?: string;
  showLabel?: boolean;
  placeholder?: string;
  options: Array<{ value: T; label: string }>;
  indicatorRight?: boolean;
  fullWidth?: boolean;
};

function SelectField<T extends string>({
  label,
  options,
  indicatorRight = false,
  fullWidth = false,
  showLabel,
  placeholder,
}: SelectFieldProps<T>) {
  const field = useFieldContext<T>();
  const id = React.useId();
  const leftClasses =
    "pl-8 pr-2 [&>span:first-child]:left-2 [&>span:first-child]:right-auto";

  const value = (field.state.value as string | undefined) ?? "";
  return (
    <div className="space-y-2">
      {label && showLabel && <Label htmlFor={id}>{label}</Label>}

      {/* SelectValue reads option labels from `items`. */}
      <Select
        value={value}
        onValueChange={(v) => field.handleChange(v as T)}
        items={options}
      >
        <SelectTrigger id={id} className={cn(fullWidth && "w-full")}>
          {value ? (
            <SelectValue />
          ) : (
            <span className="text-muted-foreground">
              {placeholder ?? "Select an option"}
            </span>
          )}
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem
              key={o.value}
              value={o.value}
              className={indicatorRight ? undefined : leftClasses}
            >
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {field.state.meta.isTouched && !field.state.meta.isValid ? (
        <p className="text-sm text-destructive">
          {field.state.meta.errors.join(", ")}
        </p>
      ) : null}
    </div>
  );
}

type ChoiceStackFieldProps<T extends string> = {
  label?: string;
  showLabel?: boolean;
  options: Array<{ value: T; label: string }>;
  fullWidth?: boolean;
  autoSubmit?: boolean;
  containerClassName?: string;
  buttonClassName?: string;
  buttonProps?: Omit<React.ComponentProps<typeof Button>, "render" | "type">;
};

function ChoiceStackField<T extends string>({
  label,
  showLabel,
  options,
  fullWidth = true,
  autoSubmit = false,
  containerClassName,
  buttonClassName,
  buttonProps,
}: ChoiceStackFieldProps<T>) {
  const field = useFieldContext<T | undefined>();
  const groupId = React.useId();
  const selected = field.state.value;

  const handleChange = (v: string) => {
    if (!v) return;
    field.handleChange(v as T);
    field.handleBlur();

    if (autoSubmit) {
      requestAnimationFrame(() => {
        const formEl = document
          .getElementById(groupId)
          ?.closest("form") as HTMLFormElement | null;
        formEl?.requestSubmit();
      });
    }
  };

  return (
    <div className="space-y-2">
      {label && showLabel && <Label htmlFor={groupId}>{label}</Label>}

      <RadioGroup
        id={groupId}
        value={selected ?? ""}
        onValueChange={handleChange}
        className={cn(
          "flex flex-col gap-2",
          fullWidth && "w-full",
          containerClassName,
        )}
      >
        {options.map((o) => {
          const id = `${groupId}-${o.value}`;
          const isActive = selected === o.value;
          return (
            <div key={o.value} className={cn(fullWidth && "w-full")}>
              <RadioGroupItem id={id} value={o.value} className="sr-only" />
              <Button
                nativeButton={false}
                render={<label htmlFor={id}>{o.label}</label>}
                variant={
                  buttonProps?.variant ?? (isActive ? "default" : "outline")
                }
                type="button"
                className={cn(
                  fullWidth && "w-full",
                  "justify-center",
                  buttonClassName,
                  buttonProps?.className,
                )}
                {...buttonProps}
              />
            </div>
          );
        })}
      </RadioGroup>

      {field.state.meta.isTouched && !field.state.meta.isValid ? (
        <p className="text-sm text-destructive">
          {field.state.meta.errors.join(", ")}
        </p>
      ) : null}
    </div>
  );
}

export const { useAppForm } = createFormHook({
  fieldContext,
  formContext,
  fieldComponents: { TextField, SelectField, ChoiceStackField },
  formComponents: {
    SubmitButton: function SubmitButton(
      props: React.ComponentProps<typeof Button>,
    ) {
      return <Button type="submit" {...props} />;
    },
  },
});
