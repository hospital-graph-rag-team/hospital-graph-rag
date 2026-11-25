import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--cg-accent-teal)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--cg-bg-main)] disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--cg-accent-teal)] text-[#041014] hover:brightness-110 font-semibold shadow-sm",
        secondary:
          "bg-[var(--cg-bg-elevated)] text-[var(--cg-text-primary)] border border-[var(--cg-border)] hover:border-[var(--cg-border-strong)] hover:bg-[var(--cg-bg-panel)]",
        outline:
          "border border-[var(--cg-border)] bg-transparent text-[var(--cg-text-primary)] hover:bg-[var(--cg-bg-elevated)] hover:border-[var(--cg-border-strong)]",
        ghost:
          "text-[var(--cg-text-secondary)] hover:text-[var(--cg-text-primary)] hover:bg-[var(--cg-bg-elevated)]",
        destructive:
          "bg-[var(--cg-error)]/15 text-[var(--cg-error)] border border-[var(--cg-error)]/30 hover:bg-[var(--cg-error)]/25",
      },
      size: {
        default: "h-9 px-3.5 py-2",
        sm: "h-8 rounded-md px-2.5 text-xs",
        lg: "h-10 rounded-lg px-5",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
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
