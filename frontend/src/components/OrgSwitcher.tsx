import { useEffect, useState } from 'react'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select, { type SelectChangeEvent } from '@mui/material/Select'
import { getOrgs, switchOrg, type OrgListItem } from '../api/orgs'

export function OrgSwitcher() {
  const [orgs, setOrgs] = useState<OrgListItem[]>([])
  const [active, setActive] = useState('')

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
    setActive(slug)
    await switchOrg(slug)
    window.location.reload()
  }

  if (orgs.length === 0) {
    return null
  }

  return (
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
      </Select>
    </FormControl>
  )
}
