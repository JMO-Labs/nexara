"use client";
/**
 * @file components/ui/Card.tsx
 * @brief Editorial card. Joy Card with optional motion wrapper for
 *        interactive hover/press feedback.
 */
import * as React from "react";
import JoyCard, { type CardProps as JoyCardProps } from "@mui/joy/Card";
import { motion } from "framer-motion";
import { spring } from "./motion";

export type CardProps = JoyCardProps & {
  interactive?: boolean;
};

export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { interactive, sx, ...rest },
  ref,
) {
  const card = (
    <JoyCard
      ref={ref}
      sx={{
        borderRadius: "lg",
        boxShadow: "sm",
        backgroundColor: "background.surface",
        ...(interactive && { cursor: "pointer" }),
        ...sx,
      }}
      {...rest}
    />
  );
  if (!interactive) return card;
  return (
    <motion.div
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.995 }}
      transition={spring}
    >
      {card}
    </motion.div>
  );
});

export default Card;
