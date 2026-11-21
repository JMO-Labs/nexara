"use client";
/**
 * @file components/home/Greeting.tsx
 * @brief Home greeting: "Good {part}, {first}" plus a long date line.
 */
import * as React from "react";

/**
 * @brief Day-part label.
 * @param d date to describe
 * @return morning, afternoon or evening
 */
export function dayPart(d: Date): "morning" | "afternoon" | "evening" {
  const h = d.getHours();
  return h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
}

/**
 * @brief Greeting header.
 * @param name full display name; first word is used
 * @return heading block
 */
export function Greeting({ name }: { name: string }) {
  const first = name.trim().split(/\s+/)[0] || "there";
  const now = new Date();
  const date = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(now);
  return (
    <header>
      <h1 className="text-[28px] md:text-[40px] font-medium leading-[1.05] tracking-tight">
        Good {dayPart(now)}, {first}
      </h1>
      <p className="mt-1 text-sm md:text-[15px] text-[var(--nx-muted)]">
        {date}
      </p>
    </header>
  );
}
