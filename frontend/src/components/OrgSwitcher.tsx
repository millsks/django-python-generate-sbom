import { useEffect, useState } from 'react'
import Button from '@mui/material/Button'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select, { type SelectChangeEvent } from '@mui/material/Select'
import Typography from '@mui/material/Typography'
import { getOrgs, switchOrg, type OrgListItem } from '../api/orgs'
import { useAuth } from '../auth/AuthProvider'
import { CreateOrgDialog } from './CreateOrgDialog'
import { AddActionIcon } from '../icons'

// Sentinel Select value for the "create a new org" item, so choosing it opens the
// create dialog (Story 2.5) instead of trying to switch to a non-existent org.
const CREATE_ORG_VALUE = '__create-org__'

export function OrgSwitcher() {
  const { isGlobalAdmin } = useAuth()
  const [orgs, setOrgs] = useState<OrgListItem[]>([])
  const [active, setActive] = useState('')
  const [createOpen, setCreateOpen] = useState(false)

  useEffect(() => {
    getOrgs()
      .then((list) => {
        setOrgs(list)
        const current = list.find((org) => org.active)
        if (current) setActive(current.slug)
      })
      .catch(() => {})
  }, [])

  async function handleChange(event: SelectChangeEvent) {
    const slug = event.target.value
    if (slug === CREATE_ORG_VALUE) {
      // Keep the current org selected; the dialog drives the actual switch on success.
      setCreateOpen(true)
      return
    }
    setActive(slug)
    await switchOrg(slug)
    window.location.reload()
  }

  if (orgs.length === 0) {
    // A non-global-admin with no orgs waits to be added — no create affordance (Story 2.12).
    if (!isGlobalAdmin) return null
    // A global admin still sees a way forward instead of an invisible switcher.
    return (
      <>
        <Button
          color="inherit"
          variant="outlined"
          size="small"
          startIcon={<AddActionIcon />}
          onClick={() => setCreateOpen(true)}
          sx={{ borderColor: 'currentColor' }}
        >
          Create organization
        </Button>
        <CreateOrgDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      </>
    )
  }

  if (orgs.length === 1) {
    // With a single org there is nothing to switch to (Story 2.19): show the org name
    // statically instead of a pointless dropdown. The active org is also visible in the
    // account menu and the side-nav footer.
    return (
      <Typography variant="body1" sx={{ color: 'inherit', fontWeight: 500 }}>
        {orgs[0].name}
      </Typography>
    )
  }

  return (
    <>
      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel id="org-switcher-label" sx={{ color: 'inherit', '&.Mui-focused': { color: 'inherit' } }}>
          Org
        </InputLabel>
        <Select
          labelId="org-switcher-label"
          label="Org"
          value={active}
          onChange={handleChange}
          // Inherit the surrounding text color so the switcher is legible in BOTH places it
          // renders: white in the red app bar, and dark on the light dashboard page. (A fixed
          // white background/text looked out of place in the banner and was invisible on the page.)
          sx={{
            color: 'inherit',
            '& .MuiOutlinedInput-notchedOutline': { borderColor: 'currentColor' },
            '& .MuiSvgIcon-root': { color: 'inherit' },
          }}
          // The open list keeps a solid surface (theme background.paper) so it stays readable.
          MenuProps={{ slotProps: { paper: { sx: { bgcolor: 'background.paper' } } } }}
        >
          {orgs.map((org) => (
            <MenuItem key={org.slug} value={org.slug}>
              {org.name}
            </MenuItem>
          ))}
          {isGlobalAdmin && (
            <MenuItem value={CREATE_ORG_VALUE} sx={{ borderTop: 1, borderColor: 'divider', gap: 1 }}>
              <AddActionIcon fontSize="small" />
              New organization
            </MenuItem>
          )}
        </Select>
      </FormControl>
      <CreateOrgDialog open={createOpen} onClose={() => setCreateOpen(false)} />
    </>
  )
}
