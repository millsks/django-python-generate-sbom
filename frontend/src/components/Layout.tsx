// App shell (Story 10.1): a persistent top app bar with auth-aware, role-aware
// navigation, the org switcher, theme toggle, and an account menu — wrapping the
// routed pages via <Outlet/>.
import { useState } from 'react'
import { Link as RouterLink, NavLink, Outlet, useNavigate } from 'react-router-dom'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import { useAuth } from '../auth/AuthProvider'
import { ThemeToggle } from '../ThemeModeProvider'
import { OrgSwitcher } from './OrgSwitcher'

function NavButton({ to, label }: { to: string; label: string }) {
  return (
    <Button
      component={NavLink}
      to={to}
      color="inherit"
      sx={{ '&.active': { textDecoration: 'underline', fontWeight: 700 } }}
    >
      {label}
    </Button>
  )
}

export function Layout() {
  const { status, activeOrg, isAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)

  async function handleLogout() {
    setAnchor(null)
    await logout()
    navigate('/login')
  }

  return (
    <>
      <AppBar position="static">
        <Toolbar sx={{ gap: 1 }}>
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{ color: 'inherit', textDecoration: 'none', mr: 2 }}
          >
            Generate SBOM
          </Typography>

          {status === 'authed' && (
            <Box component="nav" aria-label="main navigation" sx={{ display: 'flex', gap: 0.5 }}>
              <NavButton to="/upload" label="Upload" />
              <NavButton to="/history" label="History" />
              <NavButton to="/keys" label="API Keys" />
              {isAdmin && <NavButton to="/members" label="Members" />}
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />
          <ThemeToggle />

          {status === 'anon' && (
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <NavButton to="/login" label="Login" />
              <NavButton to="/register" label="Register" />
            </Box>
          )}

          {status === 'authed' && (
            <>
              <OrgSwitcher />
              <IconButton
                color="inherit"
                aria-label="Account menu"
                onClick={(event) => setAnchor(event.currentTarget)}
              >
                👤
              </IconButton>
              <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
                {activeOrg && (
                  <MenuItem disabled sx={{ opacity: '1 !important' }}>
                    <Typography variant="body2" color="text.secondary">
                      {activeOrg.name}
                    </Typography>
                  </MenuItem>
                )}
                {activeOrg && <Divider />}
                <MenuItem onClick={handleLogout}>Logout</MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
      </AppBar>
      <Outlet />
    </>
  )
}
