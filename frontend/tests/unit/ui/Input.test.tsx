/**
 * @file tests/unit/ui/Input.test.tsx
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { Input } from '@/components/ui/Input';

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe('Input', () => {
  it('renders label + helper text', () => {
    wrap(<Input label="Email" helperText="We never share." placeholder="you@example.com" />);
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('We never share.')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
  });

  it('accepts typing', async () => {
    wrap(<Input placeholder="x" />);
    const el = screen.getByPlaceholderText('x') as HTMLInputElement;
    await userEvent.type(el, 'abc');
    expect(el.value).toBe('abc');
  });
});
