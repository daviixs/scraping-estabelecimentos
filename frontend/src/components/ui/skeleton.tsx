import * as React from "react";
import { cn } from "../../lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-2xl bg-gradient-to-r from-sand-200/90 via-white to-sand-200/90",
        className
      )}
    />
  );
}
