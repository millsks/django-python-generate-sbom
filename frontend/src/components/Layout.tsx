// App shell (Story 10.1, refined in Story 12.3): a fixed app bar with global actions
// (org switcher, theme toggle, repo/docs links, account menu), a responsive side
// navigation drawer holding the primary destinations for authenticated users, the
// routed page in the main region (<Outlet/>), and a footer — all on the 12.1 theme.
import { useState, type ReactNode } from 'react'
import { Link as RouterLink, NavLink, Outlet, useNavigate } from 'react-router-dom'
import AppBar from '@mui/material/AppBar'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import IconButton from '@mui/material/IconButton'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import Toolbar from '@mui/material/Toolbar'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import ListItemIcon from '@mui/material/ListItemIcon'
import FactCheckIcon from '@mui/icons-material/FactCheck'
import GitHubIcon from '@mui/icons-material/GitHub'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import MenuIcon from '@mui/icons-material/Menu'
import { useAuth } from '../auth/AuthProvider'
import { AccountIcon, LogoutActionIcon } from '../icons'
import { APP_NAME, DOCS_URL, REPO_URL } from '../config'
import { ThemeToggle } from '../ThemeModeProvider'
import { Footer } from './Footer'
import { OrgSwitcher } from './OrgSwitcher'
import { SideNav } from './SideNav'

const DRAWER_WIDTH = 240

// Icon link to an external resource (repo / docs) — opens in a new tab with an
// accessible label and tooltip (Story 11.8).
function ExternalIconLink({ href, label, children }: { href: string; label: string; children: ReactNode }) {
  return (
    <Tooltip title={label}>
      <IconButton color="inherit" component="a" href={href} target="_blank" rel="noopener noreferrer" aria-label={label}>
        {children}
      </IconButton>
    </Tooltip>
  )
}

function NavButton({ to, label }: { to: string; label: string }) {
  return (
    <Button component={NavLink} to={to} color="inherit" sx={{ '&.active': { textDecoration: 'underline', fontWeight: 700 } }}>
      {label}
    </Button>
  )
}

export function Layout() {
  const { status, user, activeOrg, isAdmin, isGlobalAdmin, logout } = useAuth()
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const authed = status === 'authed'

  async function handleLogout() {
    setAnchor(null)
    await logout()
    navigate('/login')
  }

  const closeMobile = () => setMobileOpen(false)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar sx={{ gap: 1 }}>
          {authed && isMobile && (
            <IconButton color="inherit" aria-label="Open navigation" edge="start" onClick={() => setMobileOpen(true)}>
              <MenuIcon />
            </IconButton>
          )}
          <Box
            component={RouterLink}
            to="/"
            sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'inherit', textDecoration: 'none', mr: 2 }}
          >
            <FactCheckIcon />
            <Typography variant="h6" component="span" sx={{ fontWeight: 700, letterSpacing: '.02em', whiteSpace: 'nowrap' }}>
              {APP_NAME}
            </Typography>
          </Box>

          <Box sx={{ flexGrow: 1 }} />
          <ExternalIconLink href={DOCS_URL} label="Documentation">
            <MenuBookIcon />
          </ExternalIconLink>
          <ExternalIconLink href={REPO_URL} label="GitHub repository">
            <GitHubIcon />
          </ExternalIconLink>
          <ThemeToggle />

          {status === 'anon' && (
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              <NavButton to="/login" label="Login" />
              <NavButton to="/register" label="Register" />
            </Box>
          )}

          {authed && (
            <>
              <OrgSwitcher />
              <IconButton color="inherit" aria-label="Account menu" onClick={(event) => setAnchor(event.currentTarget)}>
                <AccountIcon />
              </IconButton>
              <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
                {user && (
                  <MenuItem disabled sx={{ opacity: '1 !important' }}>
                    <Box>
                      <Typography variant="body2">{user.email}</Typography>
                      {activeOrg && (
                        <Typography variant="caption" color="text.secondary">
                          {activeOrg.name}
                        </Typography>
                      )}
                    </Box>
                  </MenuItem>
                )}
                {user && <Divider />}
                <MenuItem onClick={handleLogout}>
                  <ListItemIcon>
                    <LogoutActionIcon fontSize="small" />
                  </ListItemIcon>
                  Logout
                </MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
      </AppBar>

      <Box sx={{ display: 'flex', flexGrow: 1 }}>
        {authed &&
          (isMobile ? (
            <Drawer
              variant="temporary"
              open={mobileOpen}
              onClose={closeMobile}
              ModalProps={{ keepMounted: true }}
              sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH, display: 'flex', flexDirection: 'column' } }}
            >
              <SideNav isAdmin={isAdmin} isGlobalAdmin={isGlobalAdmin} activeOrg={activeOrg} onNavigate={closeMobile} />
            </Drawer>
          ) : (
            <Drawer
              variant="permanent"
              sx={{
                width: DRAWER_WIDTH,
                flexShrink: 0,
                '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box', display: 'flex', flexDirection: 'column' },
              }}
            >
              <SideNav isAdmin={isAdmin} isGlobalAdmin={isGlobalAdmin} activeOrg={activeOrg} />
            </Drawer>
          ))}

        <Box component="main" sx={{ flexGrow: 1, p: 3, width: '100%', minWidth: 0 }}>
          <Toolbar />
          <Outlet />
        </Box>
      </Box>

      <Footer />
    </Box>
  )
}
