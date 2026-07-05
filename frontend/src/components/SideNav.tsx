// Side navigation (Story 12.3): the primary destinations for an authenticated user,
// plus a contextual side region (active org). Rendered inside the responsive Drawer in
// Layout — a Toolbar spacer sits it below the fixed app bar.
import { NavLink } from 'react-router-dom'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import type { SvgIconComponent } from '@mui/icons-material'
import type { OrgSummary } from '../api/auth'
import { NavIcon } from '../icons'

interface NavDest {
  to: string
  label: string
  Icon: SvgIconComponent
}

const NAV_ITEMS: NavDest[] = [
  { to: '/upload', label: 'Upload', Icon: NavIcon.upload },
  { to: '/history', label: 'History', Icon: NavIcon.history },
  { to: '/keys', label: 'API Keys', Icon: NavIcon.keys },
]

// `onNavigate` closes the temporary drawer after a selection on mobile; on the
// permanent desktop drawer it is omitted.
export function SideNav({
  isAdmin,
  activeOrg,
  onNavigate,
}: {
  isAdmin: boolean
  activeOrg: OrgSummary | null
  onNavigate?: () => void
}) {
  const items = isAdmin ? [...NAV_ITEMS, { to: '/members', label: 'Members', Icon: NavIcon.members }] : NAV_ITEMS

  return (
    <>
      <Toolbar />
      <Box component="nav" aria-label="main navigation" sx={{ overflow: 'auto' }}>
        <List>
          {items.map((item) => (
            <ListItem key={item.to} disablePadding>
              <ListItemButton
                component={NavLink}
                to={item.to}
                onClick={onNavigate}
                sx={{
                  '&.active': {
                    bgcolor: 'action.selected',
                    borderRight: 3,
                    borderColor: 'primary.main',
                    '& .MuiListItemText-primary': { fontWeight: 700 },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40, color: 'inherit' }}>
                  <item.Icon fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Box>
      <Box sx={{ mt: 'auto', p: 2 }}>
        <Divider sx={{ mb: 1 }} />
        <Typography variant="overline" color="text.secondary" component="p">
          Organization
        </Typography>
        <Typography variant="body2" noWrap>
          {activeOrg?.name ?? '—'}
        </Typography>
      </Box>
    </>
  )
}
