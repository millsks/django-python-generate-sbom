// Design system foundation (Story 12.1). The single source of truth for the app's
// visual style, built from the user-supplied brand palette.
//
// Palette choices:
//   - primary  = brand red #D71E28 (white text → 5.1:1, AA); secondary = gold #FFCD41
//     (dark text #141414 → 13:1, AA). Gold always pairs with dark text, never white.
//   - error uses a distinct deeper red (#B00020) so it never reads as the brand primary.
//   - warning/info reuse the accent spectrum (orange / indigo); success needs a green,
//     which the brand palette does not provide, so a conventional green is introduced.
//   - backgrounds/text/dividers come from the neutral ramp; dark mode lightens the
//     semantic colors for legibility on dark surfaces (standard MUI dark practice).
// Typography: a dependency-free system font stack; buttons are not upper-cased.
// The accent spectrum + gold tints are exported as reusable tokens for charts/severity.

import { createTheme, type Theme, type ThemeOptions } from '@mui/material/styles'

// Brand palette — source of truth (sampled from the reference image).
export const brand = {
  red: '#D71E28', // primary
  gold: '#FFCD41', // secondary
  goldTints: ['#FFDE84', '#FFF0C8', '#FFF7E2'] as const,
  neutral: {
    900: '#141414',
    800: '#3B3331',
    500: '#787070',
    300: '#B5ADAD',
    100: '#F4F0ED',
    0: '#FFFFFF',
  },
} as const

// Warm→cool accent spectrum: a categorical/sequential scale for charts, severity, badges.
export const accentSpectrum = ['#EB691E', '#D73F26', '#C83255', '#AA1E87', '#823291', '#5A469B'] as const

const sharedOptions: ThemeOptions = {
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h1: { fontWeight: 700, fontSize: '2.5rem', lineHeight: 1.2 },
    h2: { fontWeight: 700, fontSize: '2rem', lineHeight: 1.25 },
    h3: { fontWeight: 600, fontSize: '1.5rem', lineHeight: 1.3 },
    h4: { fontWeight: 600, fontSize: '1.25rem', lineHeight: 1.35 },
    h5: { fontWeight: 600, fontSize: '1.125rem' },
    h6: { fontWeight: 600, fontSize: '1rem' },
    subtitle1: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
    caption: { fontSize: '0.75rem' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        // Visible keyboard focus ring for every interactive element (WCAG 2.4.7).
        '*:focus-visible': { outline: `2px solid ${brand.red}`, outlineOffset: '2px' },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 8 } },
    },
    MuiCard: {
      styleOverrides: { root: { borderRadius: 12 } },
    },
    MuiAppBar: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        colorPrimary: ({ theme }: { theme: Theme }) => ({
          borderBottom: `1px solid ${theme.palette.divider}`,
        }),
      },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    MuiTextField: { defaultProps: { size: 'small' } },
    MuiTable: { defaultProps: { size: 'small' } },
  },
}

export const lightTheme = createTheme(sharedOptions, {
  palette: {
    mode: 'light',
    primary: { main: brand.red, contrastText: brand.neutral[0] },
    secondary: { main: brand.gold, contrastText: brand.neutral[900] },
    error: { main: '#B00020', contrastText: brand.neutral[0] },
    warning: { main: '#EB691E', contrastText: brand.neutral[0] },
    info: { main: '#5A469B', contrastText: brand.neutral[0] },
    success: { main: '#2E7D32', contrastText: brand.neutral[0] },
    background: { default: brand.neutral[100], paper: brand.neutral[0] },
    // #57514F (not the lighter #787070) so secondary text clears AA on the off-white bg.
    text: { primary: brand.neutral[900], secondary: '#57514F' },
    divider: brand.neutral[300],
  },
})

export const darkTheme = createTheme(sharedOptions, {
  palette: {
    mode: 'dark',
    primary: { main: brand.red, contrastText: brand.neutral[0] },
    secondary: { main: brand.gold, contrastText: brand.neutral[900] },
    error: { main: '#CF6679', contrastText: brand.neutral[900] },
    warning: { main: '#EB691E', contrastText: brand.neutral[900] },
    info: { main: '#9C8BD6', contrastText: brand.neutral[900] },
    success: { main: '#66BB6A', contrastText: brand.neutral[900] },
    background: { default: brand.neutral[900], paper: brand.neutral[800] },
    text: { primary: brand.neutral[100], secondary: brand.neutral[300] },
    divider: brand.neutral[500],
  },
})
