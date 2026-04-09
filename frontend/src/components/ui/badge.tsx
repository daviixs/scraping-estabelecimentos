import * as React from "react";

import { cn } from "../../lib/utils";

const variants = {
  ALTA: "border border-blush-200 bg-blush-50 text-blush-700",
  MEDIA: "border border-sun-200 bg-sun-50 text-sun-700",
  "M\u00c3\u2030DIA": "border border-sun-200 bg-sun-50 text-sun-700",
  "M\u00c3\u0192\u00e2\u20ac\u00b0DIA": "border border-sun-200 bg-sun-50 text-sun-700",
  BAIXA: "border border-sage-200 bg-sage-50 text-sage-700",
  default: "border border-sand-200 bg-sand-50 text-graphite/80",
} as const;

type Prioridade =
  | "ALTA"
  | "MEDIA"
  | "M\u00c3\u2030DIA"
  | "M\u00c3\u0192\u00e2\u20ac\u00b0DIA"
  | "BAIXA"
  | string
  | undefined
  | null;

export function Badge({
  label,
  className,
}: {
  label: Prioridade;
  className?: string;
}) {
  const base = variants[(label as keyof typeof variants) || "default"] || variants.default;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
        base,
        className
      )}
    >
      {label || "--"}
    </span>
  );
}
