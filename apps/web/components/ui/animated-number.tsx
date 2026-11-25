"use client";

import * as React from "react";
import { useReducedMotion } from "motion/react";

export function AnimatedNumber({
  value,
  durationMs = 550,
}: {
  value: number;
  durationMs?: number;
}) {
  const prefersReduced = useReducedMotion();
  const [displayValue, setDisplayValue] = React.useState<number>(value);
  const previousRef = React.useRef<number>(0);

  React.useEffect(() => {
    if (prefersReduced) {
      setDisplayValue(value);
      previousRef.current = value;
      return;
    }

    const start = previousRef.current;
    const end = value;
    if (start === end) {
      setDisplayValue(end);
      return;
    }

    let rafId = 0;
    const startTime = performance.now();

    const tick = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (end - start) * eased);
      setDisplayValue(current);
      if (progress < 1) {
        rafId = requestAnimationFrame(tick);
      } else {
        previousRef.current = end;
      }
    };

    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [value, durationMs, prefersReduced]);

  return (
    <span className="tabular-nums">
      {new Intl.NumberFormat("en-US").format(displayValue)}
    </span>
  );
}
