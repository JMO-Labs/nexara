'use client';
/**
 * @file components/ui/Input.tsx
 * @brief Editorial input. Bottom-border-only "underline" variant alongside
 *        Joy default. Fraunces label optional via label prop.
 */
import * as React from 'react';
import JoyInput, { type InputProps as JoyInputProps } from '@mui/joy/Input';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import FormHelperText from '@mui/joy/FormHelperText';

export type InputProps = JoyInputProps & {
  label?: React.ReactNode;
  helperText?: React.ReactNode;
  underline?: boolean;
};

export const Input = React.forwardRef<HTMLDivElement, InputProps>(function Input(
  { label, helperText, underline, error, sx, ...rest },
  ref,
) {
  const input = (
    <JoyInput
      ref={ref as never}
      error={error}
      sx={{
        ...(underline && {
          background: 'transparent',
          borderRadius: 0,
          borderBottomLeftRadius: 0,
          borderBottomRightRadius: 0,
          borderTop: 'none',
          borderLeft: 'none',
          borderRight: 'none',
          borderBottom: '1px solid',
          borderColor: 'var(--nx-palette-divider)',
          paddingInline: 0,
          '&:focus-within': {
            borderColor: 'var(--nx-palette-focusVisible)',
            outline: 'none',
            boxShadow: 'none',
          },
        }),
        ...sx,
      }}
      {...rest}
    />
  );
  if (!label && !helperText) return input;
  return (
    <FormControl error={error}>
      {label && (
        <FormLabel
          sx={{
            fontFamily: 'var(--font-display)',
            fontWeight: 500,
            letterSpacing: '0.02em',
            fontSize: '0.78rem',
            textTransform: 'uppercase',
          }}
        >
          {label}
        </FormLabel>
      )}
      {input}
      {helperText && <FormHelperText>{helperText}</FormHelperText>}
    </FormControl>
  );
});

export default Input;
