"use client";
/**
 * @file components/ui/Textarea.tsx
 * @brief Joy Textarea wrapper with optional editorial label.
 */
import * as React from "react";
import JoyTextarea, {
  type TextareaProps as JoyTextareaProps,
} from "@mui/joy/Textarea";
import FormControl from "@mui/joy/FormControl";
import FormLabel from "@mui/joy/FormLabel";
import FormHelperText from "@mui/joy/FormHelperText";

export type TextareaProps = JoyTextareaProps & {
  label?: React.ReactNode;
  helperText?: React.ReactNode;
};

export const Textarea = React.forwardRef<HTMLDivElement, TextareaProps>(
  function Textarea({ label, helperText, error, ...rest }, ref) {
    const ta = <JoyTextarea ref={ref as never} error={error} {...rest} />;
    if (!label && !helperText) return ta;
    return (
      <FormControl error={error}>
        {label && (
          <FormLabel
            sx={{
              fontFamily: "var(--font-display)",
              fontWeight: 500,
              letterSpacing: "0.02em",
              fontSize: "0.78rem",
              textTransform: "uppercase",
            }}
          >
            {label}
          </FormLabel>
        )}
        {ta}
        {helperText && <FormHelperText>{helperText}</FormHelperText>}
      </FormControl>
    );
  },
);

export default Textarea;
