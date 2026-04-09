import * as React from "react";
import { cn } from "../../lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-2xl border border-sand-200/90 bg-white/80 px-3.5 py-2.5 text-sm placeholder:text-gray-400 transition focus:border-accent/40 focus:outline-none focus:ring-2 focus:ring-accent/30",
          className
        )}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
