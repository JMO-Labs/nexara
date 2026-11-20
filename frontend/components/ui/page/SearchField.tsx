"use client";
/**
 * @file components/ui/page/SearchField.tsx
 * @brief Glass search input with optional debounced onChange.
 */
import * as React from "react";
import { Search } from "lucide-react";

export interface SearchFieldProps {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  label: string;
  debounceMs?: number;
}

/**
 * @brief Search field.
 * @param label used as aria-label
 * @param debounceMs delay before onChange fires (0 = immediate)
 * @return label wrapper with searchbox
 */
export function SearchField({
  value,
  onChange,
  placeholder,
  label,
  debounceMs = 0,
}: SearchFieldProps) {
  const [local, setLocal] = React.useState(value);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const [prev, setPrev] = React.useState(value);
  if (prev !== value) {
    setPrev(value);
    setLocal(value);
  }
  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  const handle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    setLocal(v);
    if (timer.current) clearTimeout(timer.current);
    if (debounceMs > 0) {
      timer.current = setTimeout(() => onChange(v), debounceMs);
    } else {
      onChange(v);
    }
  };
  return (
    <div className="glass-item flex min-w-0 flex-1 items-center gap-2 rounded-full px-3.5 py-1.5 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent">
      <Search className="size-4 shrink-0 text-muted" aria-hidden="true" />
      <input
        type="search"
        value={local}
        onChange={handle}
        placeholder={placeholder}
        aria-label={label}
        className="min-w-0 flex-1 appearance-none border-0 bg-transparent text-sm text-ink outline-none placeholder:text-muted"
      />
    </div>
  );
}
