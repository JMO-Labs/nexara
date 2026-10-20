"use client";
/**
 * @file components/ui/Button.tsx
 * @brief Editorial button. JoyButton wrapped in motion.span for press
 *        feedback (avoids Joy + framer-motion onDrag type clash).
 */
import * as React from "react";
import JoyButton, { type ButtonProps as JoyButtonProps } from "@mui/joy/Button";
import { motion } from "framer-motion";
import { spring } from "./motion";

export type ButtonProps = JoyButtonProps & {
  display?: boolean;
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ display, sx, ...rest }, ref) {
    return (
      <motion.span
        whileTap={{ scale: 0.97 }}
        whileHover={{ y: -1 }}
        transition={spring}
        style={{ display: "inline-flex" }}
      >
        <JoyButton
          ref={ref}
          sx={{
            ...(display && {
              fontFamily: "var(--font-display)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              fontSize: "0.78rem",
            }),
            ...sx,
          }}
          {...rest}
        />
      </motion.span>
    );
  },
);

export default Button;
