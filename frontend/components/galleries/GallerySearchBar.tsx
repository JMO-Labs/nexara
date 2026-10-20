"use client";
/**
 * @file components/galleries/GallerySearchBar.tsx
 * @brief Search input that debounces 300ms before calling onSearch.
 */
import * as React from "react";
import { Search } from "lucide-react";

export interface GallerySearchBarProps {
  onSearch: (query: string) => void;
}

/**
 * @brief Debounced gallery search field.
 * @param onSearch called with the query 300ms after the last keystroke
 * @return search input
 */
export function GallerySearchBar({ onSearch }: GallerySearchBarProps) {
  const [value, setValue] = React.useState("");
  const debounceRef = React.useRef<NodeJS.Timeout | undefined>(undefined);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = e.target.value;
    setValue(next);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSearch(next), 300);
  };

  React.useEffect(() => () => clearTimeout(debounceRef.current), []);

  return (
    <div className="relative">
      <Search
        aria-hidden="true"
        className="text-muted pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
      />
      <input
        type="search"
        aria-label="Search galleries"
        placeholder="Search galleries"
        autoComplete="off"
        value={value}
        onChange={handleChange}
        className="bg-surface text-ink placeholder:text-muted focus-visible:outline-accent h-11 w-full rounded-xl pr-3 pl-9 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2"
      />
    </div>
  );
}

export default GallerySearchBar;
