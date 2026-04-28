"use client";
/**
 * @file components/galleries/GallerySearchBar.tsx
 * @brief Ghost search input that debounces 300ms before calling onSearch.
 */
import * as React from "react";
import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import Input from "@mui/joy/Input";
import Box from "@mui/joy/Box";

export interface GallerySearchBarProps {
  onSearch: (query: string) => void;
}

export function GallerySearchBar({ onSearch }: GallerySearchBarProps) {
  const [value, setValue] = React.useState("");
  const debounceRef = React.useRef<NodeJS.Timeout>();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);

    // Clear previous timeout
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Set new debounce timeout
    debounceRef.current = setTimeout(() => {
      onSearch(newValue);
    }, 300);
  };

  React.useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  return (
    <Box sx={{ mb: 3 }}>
      <Input
        placeholder="Search galleries"
        value={value}
        onChange={handleChange}
        startDecorator={
          <MagnifyingGlassIcon
            style={{ width: 16, height: 16, opacity: 0.6 }}
          />
        }
        slotProps={{
          input: {
            autoComplete: "off",
          },
        }}
        sx={{
          "--Input_focusedHighlight": "none",
          borderBottom: "1px solid transparent",
          transition: "border-color 0.2s",
          "&:focus-within": {
            borderBottomColor: "var(--joy-palette-primary-500)",
          },
        }}
      />
    </Box>
  );
}

export default GallerySearchBar;
