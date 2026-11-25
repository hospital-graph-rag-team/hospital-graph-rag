import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium transition-colors",
  {
    variants: {
      variant: {
        neutral:
          "border-[var(--cg-border)] bg-[var(--cg-bg-elevated)] text-[var(--cg-text-secondary)]",
        teal:
          "border-[#2DD4BF]/30 bg-[#2DD4BF]/10 text-[var(--cg-accent-teal)]",
        sky:
          "border-[#38BDF8]/30 bg-[#38BDF8]/10 text-[var(--cg-accent-sky)]",
        violet:
          "border-[#818CF8]/30 bg-[#818CF8]/10 text-[var(--cg-accent-violet)]",
        success:
          "border-[#34D399]/30 bg-[#34D399]/10 text-[var(--cg-success)]",
        warning:
          "border-[#FBBF24]/30 bg-[#FBBF24]/10 text-[var(--cg-warning)]",
        error:
          "border-[#F87171]/30 bg-[#F87171]/10 text-[var(--cg-error)]",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
