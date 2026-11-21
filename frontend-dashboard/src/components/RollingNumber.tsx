"use client";

import React, { useEffect, useState } from "react";
import { parseCents, formatUsd } from "@/lib/money";

interface RollingNumberProps {
  value: string | number;
  durationMs?: number;
  prefix?: string;
  decimals?: number;
}

export const RollingNumber: React.FC<RollingNumberProps> = ({
  value,
  durationMs = 900,
  prefix = "$",
  decimals = 2,
}) => {
  const targetCents = parseCents(value);
  const targetNum = Number(targetCents) / 100;
  const [displayValue, setDisplayValue] = useState<number>(targetNum);
  const [isFinished, setIsFinished] = useState<boolean>(true);

  useEffect(() => {
    let startTimestamp: number | null = null;
    const startValue = displayValue;
    const endValue = targetNum;
    const change = endValue - startValue;

    if (change === 0) {
      setIsFinished(true);
      return;
    }

    setIsFinished(false);

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / durationMs, 1);
      // Apple-style cubic deceleration
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(startValue + change * easeOut);

      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        setDisplayValue(endValue);
        setIsFinished(true);
      }
    };

    const animId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animId);
    // Animates from whatever is on screen; re-running on displayValue would restart every frame
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetNum, durationMs]);

  if (isFinished && prefix === "$") {
    return (
      <span className="font-mono tabular-nums">
        {formatUsd(value, { hideCents: decimals === 0 })}
      </span>
    );
  }

  return (
    <span className="font-mono tabular-nums">
      {prefix}
      {displayValue.toLocaleString("en-US", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}
    </span>
  );
};
