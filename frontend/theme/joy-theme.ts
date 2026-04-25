/**
 * @file theme/joy-theme.ts
 * @brief MUI Joy CSS-vars theme implementing Warm Editorial palette.
 *        Light = cream paper / ink text / terracotta primary / teal accent.
 *        Dark  = ink-tinted paper / fog text / softened terracotta.
 */
import { extendTheme } from '@mui/joy/styles';
import { colors, radius, elevation, fontStacks } from './tokens';

export const joyTheme = extendTheme({
  cssVarPrefix: 'nx',
  colorSchemes: {
    light: {
      palette: {
        primary: {
          50: '#FBEEEC',
          100: '#F4D4CF',
          200: '#E8A89F',
          300: '#DC7C6F',
          400: '#D05F50',
          500: colors.terracotta,
          600: colors.terracottaDeep,
          700: '#7E2C20',
          800: '#612218',
          900: '#451810',
          solidBg: 'var(--nx-palette-primary-500)',
          solidHoverBg: 'var(--nx-palette-primary-600)',
          solidActiveBg: 'var(--nx-palette-primary-700)',
          plainColor: 'var(--nx-palette-primary-600)',
        },
        neutral: {
          50: colors.paper,
          100: colors.fog,
          200: colors.fogDeep,
          300: '#B8AC9A',
          400: '#8A7F6F',
          500: '#5C5346',
          600: '#3F392E',
          700: colors.ink,
          800: '#1F1E1C',
          900: '#0F0E0D',
        },
        success: { 500: colors.sage, solidBg: colors.sage },
        warning: { 500: colors.ochre, solidBg: colors.ochre },
        danger: { 500: colors.rose, solidBg: colors.rose },
        background: {
          body: colors.paper,
          surface: '#FBF7EF',
          level1: colors.fog,
          level2: colors.fogDeep,
          popup: '#FFFCF5',
        },
        text: {
          primary: colors.ink,
          secondary: '#5C5346',
          tertiary: '#8A7F6F',
        },
        divider: 'rgba(43, 42, 40, 0.10)',
        focusVisible: colors.teal,
      },
    },
    dark: {
      palette: {
        primary: {
          50: '#451810',
          100: '#612218',
          200: '#7E2C20',
          300: colors.terracottaDeep,
          400: colors.terracotta,
          500: colors.terracottaSoft,
          600: '#E58275',
          700: '#EFA89E',
          800: '#F6CCC5',
          900: '#FBEEEC',
        },
        neutral: {
          50: '#0F0E0D',
          100: '#1F1E1C',
          200: colors.paperDark,
          300: '#2B2825',
          400: '#3F392E',
          500: '#5C5346',
          600: '#8A7F6F',
          700: '#B8AC9A',
          800: colors.fogDeep,
          900: colors.paper,
        },
        success: { 500: colors.sage },
        warning: { 500: colors.ochre },
        danger: { 500: colors.rose },
        background: {
          body: colors.paperDark,
          surface: '#221F1C',
          level1: '#2B2825',
          level2: '#3F392E',
          popup: '#221F1C',
        },
        text: {
          primary: colors.paper,
          secondary: colors.fogDeep,
          tertiary: '#8A7F6F',
        },
        divider: 'rgba(245, 239, 230, 0.10)',
        focusVisible: '#5FA0B5',
      },
    },
  },
  fontFamily: {
    body: 'var(--font-body), ' + fontStacks.body,
    display: 'var(--font-display), ' + fontStacks.display,
    code: 'var(--font-mono), ' + fontStacks.mono,
  },
  radius: {
    xs: '4px',
    sm: radius.sm,
    md: radius.md,
    lg: radius.lg,
    xl: radius.xl,
  },
  shadow: {
    xs: elevation.xs,
    sm: elevation.sm,
    md: elevation.md,
    lg: elevation.lg,
  },
  typography: {
    'h1': {
      fontFamily: 'var(--font-display)',
      fontWeight: 600,
      fontSize: 'clamp(2.25rem, 4vw, 3.5rem)',
      lineHeight: 1.05,
      letterSpacing: '-0.02em',
    },
    'h2': {
      fontFamily: 'var(--font-display)',
      fontWeight: 600,
      fontSize: 'clamp(1.75rem, 3vw, 2.5rem)',
      lineHeight: 1.1,
      letterSpacing: '-0.015em',
    },
    'h3': {
      fontFamily: 'var(--font-display)',
      fontWeight: 500,
      fontSize: '1.5rem',
      lineHeight: 1.2,
    },
    'h4': {
      fontFamily: 'var(--font-display)',
      fontWeight: 500,
      fontSize: '1.25rem',
      lineHeight: 1.25,
    },
    'title-lg': { fontWeight: 600, fontSize: '1.125rem' },
    'body-md': { lineHeight: 1.55 },
    'body-sm': { lineHeight: 1.5 },
  },
  components: {
    JoyButton: {
      styleOverrides: {
        root: ({ ownerState }) => ({
          borderRadius: radius.md,
          fontWeight: 500,
          letterSpacing: '0.005em',
          ...(ownerState.size === 'lg' && { paddingInline: '1.25rem' }),
        }),
      },
    },
    JoyCard: {
      styleOverrides: {
        root: {
          borderRadius: radius.lg,
          borderColor: 'var(--nx-palette-divider)',
          transition: 'box-shadow 240ms ease, transform 240ms ease',
        },
      },
    },
    JoyInput: {
      styleOverrides: {
        root: {
          borderRadius: radius.sm,
          '--Input-focusedHighlight': colors.teal,
        },
      },
    },
    JoyTypography: {
      styleOverrides: {
        // Joy maps `color="neutral"` to neutral.plainColor, which lands on
        // a low-contrast tone in dark mode. Route it to text.secondary
        // (theme-aware: dim in light, light in dark) for readable copy.
        root: ({ ownerState }) => ({
          ...(ownerState.color === 'neutral' && {
            color: 'var(--nx-palette-text-secondary)',
          }),
        }),
      },
    },
    JoyModal: {
      styleOverrides: {
        backdrop: {
          backdropFilter: 'blur(6px)',
          backgroundColor: 'rgba(43, 42, 40, 0.32)',
        },
      },
    },
  },
});

export default joyTheme;
