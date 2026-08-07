import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold transition-all duration-200 focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-slate-200 bg-slate-100 text-slate-700",
        critical:
          "border-rose-200/60 bg-rose-100/80 text-rose-700 shadow-sm",
        high: "border-amber-200/60 bg-amber-100/80 text-amber-800 shadow-sm",
        medium:
          "border-yellow-200/60 bg-yellow-100/80 text-yellow-800",
        low: "border-emerald-200/60 bg-emerald-100/80 text-emerald-800",
        outline: "border-slate-300 text-slate-600 bg-white/50",
        open: "border-sky-200/60 bg-sky-100/80 text-sky-800",
        in_progress:
          "border-indigo-200/60 bg-indigo-100/80 text-indigo-800",
        closed: "border-slate-200 bg-slate-100 text-slate-500",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };