"use client";
/**
 * @file hooks/useEventCountdown.ts
 * @brief Live countdown to event start (ticks every 30s).
 * Returns { days, hours, minutes } based on time until event.starts_at.
 */
import { useEffect, useState } from "react";
import type { EventItem } from "@/lib/api/events";

export interface Countdown {
  days: number;
  hours: number;
  minutes: number;
}

export function useEventCountdown(event: EventItem): Countdown {
  const [countdown, setCountdown] = useState<Countdown>(() =>
    calculateCountdown(event),
  );

  useEffect(() => {
    const updateCountdown = () => {
      setCountdown(calculateCountdown(event));
    };

    // Update immediately, then every 30 seconds
    updateCountdown();
    const interval = setInterval(updateCountdown, 30_000);

    return () => clearInterval(interval);
  }, [event]);

  return countdown;
}

function calculateCountdown(event: EventItem): Countdown {
  const now = new Date();
  const start = new Date(event.starts_at);
  const diff = start.getTime() - now.getTime();

  if (diff <= 0) {
    return { days: 0, hours: 0, minutes: 0 };
  }

  const totalMinutes = Math.floor(diff / 60_000);
  const days = Math.floor(totalMinutes / (24 * 60));
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;

  return { days, hours, minutes };
}
