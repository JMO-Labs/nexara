"use client";
/**
 * @file components/layout/SimpleModeSync.tsx
 * @brief Mirrors the user's simple_mode setting (when the community feature
 *        is on) to `<html data-simple>` and the simple-mode store.
 */
import { useEffect } from "react";
import { useFeature } from "@/hooks/useFeature";
import { useUserSettings } from "@/hooks/useSettings";
import { useSimpleMode } from "@/stores/simpleMode";

/**
 * @brief Render-less sync component; mount once in Shell.
 * @return null
 */
export function SimpleModeSync() {
  const featureOn = useFeature("simple_mode");
  const { data } = useUserSettings();
  const on = featureOn && data?.simple_mode === true;
  const setOn = useSimpleMode((s) => s.setOn);

  useEffect(() => {
    setOn(on);
    const root = document.documentElement;
    if (on) root.dataset.simple = "1";
    else delete root.dataset.simple;
    return () => {
      delete root.dataset.simple;
    };
  }, [on, setOn]);

  return null;
}
