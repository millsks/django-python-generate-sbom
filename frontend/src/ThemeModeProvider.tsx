import { useEffect, useMemo, useState, type ReactNode } from 'react'
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

  function toggle() {
    setOverride(mode === 'dark' ? 'light' : 'dark')
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Tooltip title={mode === 'dark' ? 'Switch to light' : 'Switch to dark'}>
        <IconButton
          onClick={toggle}
          aria-label="Toggle light/dark theme"
          sx={{ position: 'fixed', top: 8, right: 8, zIndex: 1300 }}
        >
          {mode === 'dark' ? '☀️' : '🌙'}
        </IconButton>
      </Tooltip>
      {children}
    </ThemeProvider>
  )
}
