"use client";
/**
 * @file components/home/WelcomeBanner.tsx
 * @brief Home greeting: day-part line plus "Hi {firstName}." headline.
 */
import * as React from "react";

/**
 * @brief Day-part label such as "Tuesday evening".
 * @param d date to describe
 * @return weekday plus morning/afternoon/evening
 */
export function dayPart(d: Date): string {
  const h = d.getHours();
  const part = h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
  return `${d.toLocaleDateString("en-US", { weekday: "long" })} ${part}`;
}

export interface WelcomeBannerProps {
  userName: string;
}

/**
 * @brief Greeting header.
 * @param userName full display name; first word is used
 * @return heading block
 */
export function WelcomeBanner({ userName }: WelcomeBannerProps) {
  const first = userName.trim().split(/\s+/)[0] || "there";
  return (
    <header className="mb-6">
      <p className="text-muted text-base">{dayPart(new Date())}</p>
      <h1 className="font-black text-4xl md:text-5xl leading-[1.05] tracking-tight">
        Hi {first}.
      </h1>
    </header>
  );
}

export default WelcomeBanner;
