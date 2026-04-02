import * as React from "react";
import { cn } from "../../lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-xl bg-gradient-to-r from-sand-200 via-sand-100 to-sand-200",
        className
      )}
    />
  );
}
