import * as React from "react";
import { cn } from "../../lib/utils";

const variants = {
  ALTA: "bg-red-100 text-red-800 border border-red-200",
  "MÉDIA": "bg-amber-100 text-amber-800 border border-amber-200",
  BAIXA: "bg-emerald-100 text-emerald-800 border border-emerald-200",
  default: "bg-sand-200 text-graphite border border-sand-300",
} as const;

type Prioridade = "ALTA" | "MÉDIA" | "BAIXA" | string | undefined | null;

export function Badge({
  label,
  className,
}: {
  label: Prioridade;
  className?: string;
}) {
  const base =
    variants[(label as keyof typeof variants) || "default"] || variants.default;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
        base,
        className
      )}
    >
      {label || "—"}
    </span>
  );
}
