// Shared loading / empty / error state components (Story 12.4). Pages that fetch data
// render these so every screen handles its async states the same way, on the 12.1 theme.
import type { ComponentType, ReactNode } from 'react'
import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import Typography from '@mui/material/Typography'
import type { SvgIconProps } from '@mui/material/SvgIcon'

// Centered spinner for a first load. `label` is the accessible name for the busy region.
export function LoadingState({ label = 'Loading' }: { label?: string }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
      <CircularProgress aria-label={label} />
    </Box>
  )
}

// A quiet, centered "nothing here" state — an optional icon, a title, and a hint.
export function EmptyState({
  title,
  message,
  icon: Icon,
  action,
}: {
  title: string
  message?: string
  icon?: ComponentType<SvgIconProps>
  action?: ReactNode
}) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 1.5,
        py: 6,
        textAlign: 'center',
        color: 'text.secondary',
      }}
    >
      {Icon && <Icon sx={{ fontSize: 48, opacity: 0.6 }} />}
      <Typography variant="h6" component="p" color="text.primary">
        {title}
      </Typography>
      {message && (
        <Typography variant="body2" sx={{ maxWidth: 420 }}>
          {message}
        </Typography>
      )}
      {action}
    </Box>
  )
}

// A consistent error banner for a failed fetch/action.
export function ErrorState({ message, title = 'Something went wrong' }: { message: string; title?: string }) {
  return (
    <Alert severity="error">
      <AlertTitle>{title}</AlertTitle>
      {message}
    </Alert>
  )
}
