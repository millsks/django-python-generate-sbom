import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import CssBaseline from '@mui/material/CssBaseline'
import IconButton from '@mui/material/IconButton'
import Tooltip from '@mui/material/Tooltip'
import { ThemeProvider } from '@mui/material/styles'
import useMediaQuery from '@mui/material/useMediaQuery'
import { darkTheme, lightTheme } from './theme'

type Mode = 'light' | 'dark'
const STORAGE_KEY = 'theme-mode'

function storedMode(): Mode | null {
  const value = localStorage.getItem(STORAGE_KEY)
  return value === 'light' || value === 'dark' ? value : null
}

interface ThemeModeValue {
  mode: Mode
  toggle: () => void
}

const ThemeModeContext = createContext<ThemeModeValue | null>(null)

export function useThemeMode(): ThemeModeValue {
  const value = useContext(ThemeModeContext)
  if (!value) throw new Error('useThemeMode must be used within a ThemeModeProvider')
  return value
}

export function ThemeModeProvider({ children }: { children: ReactNode }) {
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)')
  const [override, setOverride] = useState<Mode | null>(storedMode)

  const mode: Mode = override ?? (prefersDark ? 'dark' : 'light')

  useEffect(() => {
    if (override) {
      localStorage.setItem(STORAGE_KEY, override)
    }
  }, [override])

  const theme = useMemo(() => (mode === 'dark' ? darkTheme : lightTheme), [mode])
  const value = useMemo<ThemeModeValue>(
    () => ({ mode, toggle: () => setOverride(mode === 'dark' ? 'light' : 'dark') }),
    [mode],
  )

  return (
    <ThemeModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  )
}

// The theme toggle, rendered in the app bar (Story 10.1) — previously a fixed
// floating button inside the provider.
export function ThemeToggle() {
  const { mode, toggle } = useThemeMode()
  return (
    <Tooltip title={mode === 'dark' ? 'Switch to light' : 'Switch to dark'}>
      <IconButton onClick={toggle} aria-label="Toggle light/dark theme" color="inherit">
        {mode === 'dark' ? '☀️' : '🌙'}
      </IconButton>
    </Tooltip>
  )
}
