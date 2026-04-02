import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 active:translate-y-[1px]",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-white shadow-md shadow-accent/25 hover:shadow-lg hover:shadow-accent/30 focus-visible:ring-accent/80 ring-offset-sand-100",
        ghost:
          "bg-white/80 text-graphite border border-sand-200 hover:-translate-y-[1px] hover:shadow-sm ring-offset-sand-100",
        outline:
          "border border-sand-200 bg-white text-graphite hover:bg-sand-50 ring-offset-sand-100",
        subtle:
          "bg-graphite text-sand-50 hover:bg-graphite/90 ring-offset-sand-100",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-5 text-base",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
