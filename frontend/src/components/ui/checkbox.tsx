import * as React from "react";
import { cn } from "../../lib/utils";

type Props = React.InputHTMLAttributes<HTMLInputElement>;

export function Checkbox({ className, ...props }: Props) {
  return (
    <label className="inline-flex items-center gap-2 text-sm font-medium text-graphite">
      <input
        type="checkbox"
        className={cn(
          "h-4 w-4 rounded border-sand-300 text-accent focus:ring-2 focus:ring-accent/50",
          className
        )}
        {...props}
      />
      <span>{props["aria-label"] || props.value || ""}</span>
    </label>
  );
}
